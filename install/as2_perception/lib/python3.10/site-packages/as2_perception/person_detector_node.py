#!/usr/bin/env python3
import math
from typing import Optional, List

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Header
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose, BoundingBox2D

from cv_bridge import CvBridge

import cv2
from ultralytics import YOLO


class PersonDetectorNode(Node):
    def __init__(self):
        super().__init__("person_detector")

        # ---------------- Parameters ----------------
        self.declare_parameter("image_topic", "sensor_measurements/gimbal0/hd_camera1_d0/image_raw")
        self.declare_parameter("camera_info_topic", "sensor_measurements/gimbal0/hd_camera1_d0/camera_info")
        self.declare_parameter("detections_topic", "perception/person_detections")
        self.declare_parameter("debug_image_topic", "perception/person_debug_image")

        self.declare_parameter("model", "yolov8n.pt")  # start small; later you can swap to yolov8s.pt etc.
        self.declare_parameter("device", "cpu")        # "cpu", "0" for cuda:0 if available
        self.declare_parameter("imgsz", 640)           # inference size
        self.declare_parameter("conf_thres", 0.5)
        self.declare_parameter("iou_thres", 0.45)
        self.declare_parameter("publish_debug_image", True)

        self.image_topic = self.get_parameter("image_topic").value
        self.camera_info_topic = self.get_parameter("camera_info_topic").value
        self.detections_topic = self.get_parameter("detections_topic").value
        self.debug_image_topic = self.get_parameter("debug_image_topic").value

        model_path = self.get_parameter("model").value
        device = self.get_parameter("device").value
        self.imgsz = int(self.get_parameter("imgsz").value)
        self.conf_thres = float(self.get_parameter("conf_thres").value)
        self.iou_thres = float(self.get_parameter("iou_thres").value)
        self.publish_debug_image = bool(self.get_parameter("publish_debug_image").value)

        # ---------------- YOLO ----------------
        self.get_logger().info(f"Loading YOLO model: {model_path} (device={device})")
        self.model = YOLO(model_path)
        # ultralytics uses device in predict call; keep string

        self.device = device
        self.bridge = CvBridge()

        self.last_camera_info: Optional[CameraInfo] = None

        # ---------------- ROS I/O ----------------
        self.sub_cam_info = self.create_subscription(
            CameraInfo, self.camera_info_topic, self._on_camera_info, 10
        )
        self.sub_img = self.create_subscription(
            Image, self.image_topic, self._on_image, 10
        )

        self.pub_det = self.create_publisher(Detection2DArray, self.detections_topic, 10)
        self.pub_dbg = self.create_publisher(Image, self.debug_image_topic, 10) if self.publish_debug_image else None

        self.get_logger().info(f"Subscribed image: {self.image_topic}")
        self.get_logger().info(f"Publishing detections: {self.detections_topic}")
        if self.publish_debug_image:
            self.get_logger().info(f"Publishing debug image: {self.debug_image_topic}")

    def _on_camera_info(self, msg: CameraInfo):
        self.last_camera_info = msg

    def _on_image(self, msg: Image):
        # Convert ROS Image -> OpenCV (BGR)
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().warn(f"cv_bridge conversion failed: {e}")
            return

        # Run YOLO
        try:
            results = self.model.predict(
                source=frame,
                imgsz=self.imgsz,
                conf=self.conf_thres,
                iou=self.iou_thres,
                device=self.device,
                verbose=False
            )
        except Exception as e:
            self.get_logger().error(f"YOLO inference failed: {e}")
            return

        det_msg = Detection2DArray()
        det_msg.header = msg.header if msg.header.frame_id else Header(stamp=msg.header.stamp, frame_id="camera")

        dbg = frame.copy() if self.publish_debug_image else None

        # Ultralytics returns one result per image
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes

            # class names mapping
            names = results[0].names  # dict {id: name}

            for b in boxes:
                cls_id = int(b.cls.item()) if b.cls is not None else -1
                score = float(b.conf.item()) if b.conf is not None else 0.0
                cls_name = names.get(cls_id, str(cls_id))

                # We only keep persons (COCO: "person")
                # If you later fine-tune VisDrone, class names might differ; adjust here.
                if cls_name != "person":
                    continue

                # xyxy pixel coords
                x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
                w = max(0.0, x2 - x1)
                h = max(0.0, y2 - y1)
                cx = x1 + w * 0.5
                cy = y1 + h * 0.5

                d = Detection2D()
                d.header = det_msg.header

                bbox = BoundingBox2D()
                bbox.center.position.x = cx
                bbox.center.position.y = cy
                bbox.size_x = w
                bbox.size_y = h
                d.bbox = bbox

                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = "person"
                hyp.hypothesis.score = score
                # pose left default (2D detection only)
                d.results.append(hyp)

                det_msg.detections.append(d)

                # Debug draw
                if dbg is not None:
                    cv2.rectangle(dbg, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(
                        dbg, f"person {score:.2f}",
                        (int(x1), max(0, int(y1) - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                    )

        self.pub_det.publish(det_msg)

        if self.pub_dbg is not None and dbg is not None:
            try:
                dbg_msg = self.bridge.cv2_to_imgmsg(dbg, encoding="bgr8")
                dbg_msg.header = det_msg.header
                self.pub_dbg.publish(dbg_msg)
            except Exception as e:
                self.get_logger().warn(f"Failed to publish debug image: {e}")


def main():
    rclpy.init()
    node = PersonDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

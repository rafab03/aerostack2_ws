// Copyright 2023 Universidad Politécnica de Madrid
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
//    * Redistributions of source code must retain the above copyright
//      notice, this list of conditions and the following disclaimer.
//
//    * Redistributions in binary form must reproduce the above copyright
//      notice, this list of conditions and the following disclaimer in the
//      documentation and/or other materials provided with the distribution.
//
//    * Neither the name of the Universidad Politécnica de Madrid nor the names of its
//      contributors may be used to endorse or promote products derived from
//      this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.


/*!*******************************************************************************************
 *  \file       position_motion.cpp
 *  \brief      This file contains the implementation of the PositionMotion class.
 *  \authors    Miguel Fernández Cortizas
 *              Pedro Arias Pérez
 *              David Pérez Saura
 *              Rafael Pérez Seguí
 ********************************************************************************/

#include "as2_motion_reference_handlers/position_motion.hpp"

namespace as2
{
namespace motionReferenceHandlers
{

PositionMotion::PositionMotion(as2::Node * node_ptr, const std::string & ns)
: BasicMotionReferenceHandler(node_ptr, ns)
{
  desired_control_mode_.yaw_mode = as2_msgs::msg::ControlMode::NONE;
  desired_control_mode_.control_mode = as2_msgs::msg::ControlMode::POSITION;

  // IMPORTANT:
  // Position references in frames like "earth", "<ns>/map", "<ns>/odom" are ENU-like (local navigation frame).
  // If reference_frame stays UNDEFINED_FRAME, the controller may ignore it or behave unpredictably.
  desired_control_mode_.reference_frame = as2_msgs::msg::ControlMode::LOCAL_ENU_FRAME;
}

bool PositionMotion::ownSendCommand()
{
  // Ensure reference frame is always valid for POSITION control mode
  desired_control_mode_.reference_frame = as2_msgs::msg::ControlMode::LOCAL_ENU_FRAME;

  bool send_pose = sendPoseCommand();
  bool send_twist = sendTwistCommand();
  return send_pose && send_twist;
}

bool PositionMotion::sendPositionCommandWithYawAngle(
  const std::string & frame_id_pose,
  const float & x,
  const float & y,
  const float & z,
  const float & yaw_angle,
  const std::string & frame_id_twist,
  const float & vx,
  const float & vy,
  const float & vz)
{
  return sendPositionCommandWithYawAngle(
    frame_id_pose, x, y, z, tf2::toMsg(tf2::Quaternion(tf2::Vector3(0, 0, 1), yaw_angle)),
    frame_id_twist, vx, vy, vz);
}

bool PositionMotion::sendPositionCommandWithYawAngle(
  const std::string & frame_id_pose,
  const float & x,
  const float & y,
  const float & z,
  const geometry_msgs::msg::Quaternion & q,
  const std::string & frame_id_twist,
  const float & vx,
  const float & vy,
  const float & vz)
{
  geometry_msgs::msg::PoseStamped pose_msg;
  pose_msg.header.frame_id = frame_id_pose;
  pose_msg.pose.position.x = x;
  pose_msg.pose.position.y = y;
  pose_msg.pose.position.z = z;
  pose_msg.pose.orientation = q;

  geometry_msgs::msg::TwistStamped twist_msg;
  twist_msg.header.frame_id = frame_id_twist;
  twist_msg.twist.linear.x = vx;
  twist_msg.twist.linear.y = vy;
  twist_msg.twist.linear.z = vz;

  rclcpp::Time stamp = node_ptr_->now();
  pose_msg.header.stamp = stamp;
  twist_msg.header.stamp = stamp;

  return sendPositionCommandWithYawAngle(pose_msg, twist_msg);
}

bool PositionMotion::sendPositionCommandWithYawAngle(
  const geometry_msgs::msg::PoseStamped & pose,
  const geometry_msgs::msg::TwistStamped & twist)
{
  if (pose.header.frame_id.empty() || twist.header.frame_id.empty()) {
    RCLCPP_ERROR(node_ptr_->get_logger(), "Frame id is empty");
    return false;
  }

  // We operate in an ENU navigation frame (earth / map / odom).
  // Set this ALWAYS to avoid UNDEFINED_FRAME in controller mode.
  desired_control_mode_.reference_frame = as2_msgs::msg::ControlMode::LOCAL_ENU_FRAME;

  // Optional sanity check: pose and twist should usually be expressed in the same frame.
  if (pose.header.frame_id != twist.header.frame_id) {
    RCLCPP_WARN(
      node_ptr_->get_logger(),
      "Pose frame_id (%s) != Twist frame_id (%s). Using pose frame as reference.",
      pose.header.frame_id.c_str(), twist.header.frame_id.c_str());
  }

  desired_control_mode_.yaw_mode = as2_msgs::msg::ControlMode::YAW_ANGLE;
  this->command_pose_msg_ = pose;
  this->command_twist_msg_ = twist;

  return this->ownSendCommand();
}

bool PositionMotion::sendPositionCommandWithYawSpeed(
  const std::string & frame_id_pose,
  const float & x,
  const float & y,
  const float & z,
  const float & yaw_speed,
  const std::string & frame_id_twist,
  const float & vx,
  const float & vy,
  const float & vz)
{
  geometry_msgs::msg::PoseStamped pose_msg;
  pose_msg.header.frame_id = frame_id_pose;
  pose_msg.pose.position.x = x;
  pose_msg.pose.position.y = y;
  pose_msg.pose.position.z = z;

  geometry_msgs::msg::TwistStamped twist_msg;
  twist_msg.header.frame_id = frame_id_twist;
  twist_msg.twist.linear.x = vx;
  twist_msg.twist.linear.y = vy;
  twist_msg.twist.linear.z = vz;
  twist_msg.twist.angular.z = yaw_speed;

  rclcpp::Time stamp = node_ptr_->now();
  pose_msg.header.stamp = stamp;
  twist_msg.header.stamp = stamp;

  return sendPositionCommandWithYawSpeed(pose_msg, twist_msg);
}

bool PositionMotion::sendPositionCommandWithYawSpeed(
  const geometry_msgs::msg::PoseStamped & pose,
  const geometry_msgs::msg::TwistStamped & twist)
{
  if (pose.header.frame_id.empty() || twist.header.frame_id.empty()) {
    RCLCPP_ERROR(node_ptr_->get_logger(), "Frame id is empty");
    return false;
  }

  // Same rationale as yaw angle: ensure reference frame is valid
  desired_control_mode_.reference_frame = as2_msgs::msg::ControlMode::LOCAL_ENU_FRAME;

  if (pose.header.frame_id != twist.header.frame_id) {
    RCLCPP_WARN(
      node_ptr_->get_logger(),
      "Pose frame_id (%s) != Twist frame_id (%s). Using pose frame as reference.",
      pose.header.frame_id.c_str(), twist.header.frame_id.c_str());
  }

  desired_control_mode_.yaw_mode = as2_msgs::msg::ControlMode::YAW_SPEED;
  this->command_pose_msg_ = pose;
  this->command_twist_msg_ = twist;

  return this->ownSendCommand();
}

}    // namespace motionReferenceHandlers
}  // namespace as2

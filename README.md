# aerostack2_ws — Perception + Swarm (Docker)

Este readme contiene los pasos necesarios para clonar el repositorio de Aerostack2, repositorio sobre el que se han desarrollado los paquetes necesarios para el correcto cumplimiento de los requisitos de este proyecto.

---

## 1) Clonar el repositorio

```bash
# Clona el repo
git clone https://github.com/rafab03/aerostack2_ws.git
cd aerostack2_ws
```

---

## 2) Crear carpeta docker

```bash
mkdir -p docker
```

Colocar Dockerfile dentro de la carpeta `docker/`.

---

## 3) Construir imagen (Dockerfile)

```bash
cd docker
docker build --no-cache -t aerostack2_perception:latest .
```

---

## 4) Ejecutar imagen (construir contenedor, dentro de la caepeta docker)

```bash
xhost +local:docker

sudo docker run -it \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ~/aerostack2_ws:/root/aerostack2_ws \
  aerostack2_perception:latest bash
```

Una vez ejecutamos este comando estamos dentro del contenedor. Si queremos levantar otra terminal dentro de la sesión, debemos ejecutar el siguiente comando

## 5) Ver ID del container

```bash
docker ps
```
Copiamos el ID y ejecutamos el siguiente comando:

```bash
docker exec -it ID bash
```


## 6) Compilación

Compilamos los paquetes del repositorio de Aerostack2 y los desarrollados para este trabajo
```bash
colcon build
```
Y sourceamos el workspace una vez creados las dependencias necesarias:
```bash
source install/setup.bash
```
## 7) Lanzamiento de comandos:

Ejecutar en este orden (una terminal por comando)

### 1. Simulación

```bash
ros2 launch as2_gazebo_assets launch_simulation.py \
  simulation_config_file:=/root/aerostack2_ws/src/aerostack2/as2_aerial_platforms/as2_platform_gazebo/config/empty_world.yaml
```

---

### 2. Static TF

```bash
ros2 launch as2_project_bringup 05_static_tf_3drones.launch.py
```

---

### 3. Plataforma

```bash
ros2 launch as2_project_bringup 01_platform_3drones.launch.py \
  simulation_config_file:=/root/aerostack2_ws/src/aerostack2/as2_aerial_platforms/as2_platform_gazebo/config/empty_world.yaml
```

---

### 4. State estimator

```bash
ros2 launch as2_project_bringup 02_state_estimator_3drones.launch.py
```

---

### 5. Behaviors

```bash
ros2 launch as2_project_bringup 03_behaviors_3drones.launch.py
```

---

### 6. Motion controller

```bash
ros2 launch as2_project_bringup 04_motion_controller_3drones.launch.py
```

---

### 7. Teleoperación teclado

```bash
ros2 launch as2_keyboard_teleoperation as2_keyboard_teleoperation_launch.py \
  namespace:=drone0,drone1,drone2 use_sim_time:=true
```

---
### 8. Percepción — ray-to-ground

```bash
ros2 launch as2_project_bringup 07_swarm_person_perception_rayground.launch.py
```

Detección + segunda aproximación con rayo guiado.

---

### 9. Fusión CI

```bash
ros2 launch as2_swarm_fusion_ci swarm_ci_fusion.launch.py
```

Método CI. Requiere ejecutar el paso 8.

---

### 10. Fusión EKF

```bash
ros2 launch as2_project_bringup 08_swarm_person_perception_rayground_ekf.launch.py
```

Algoritmo EKF implementado. Requiere ejecutar el paso 8.

---

### 11. Percepción multi-persona con tracking

```bash
ros2 launch as2_project_bringup 09_swarm_person_perception_rayground_tracking.launch.py
```

YOLO + ray-to-ground + asociador de IDs (seguimiento de múltiples personas).

---

### 12. Fusión CI multi-persona

```bash
ros2 launch as2_swarm_ci_fusion_people swarm_ci_fusion_people.launch.py
```

Fusión por método CI para múltiples personas (requiere paso 11).

---

### 13. Fusión EKF multi-persona

```bash
ros2 launch as2_project_bringup 10_swarm_person_perception_rayground_tracking_ekf_people.launch.py
```

Fusión EKF para múltiples personas (requiere paso 11).






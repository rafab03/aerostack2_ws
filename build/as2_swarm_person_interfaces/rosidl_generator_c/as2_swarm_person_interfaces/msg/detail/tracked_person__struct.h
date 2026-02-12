// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from as2_swarm_person_interfaces:msg/TrackedPerson.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__STRUCT_H_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.h"
// Member 'source'
#include "rosidl_runtime_c/string.h"
// Member 'pose'
#include "geometry_msgs/msg/detail/pose_with_covariance__struct.h"

/// Struct defined in msg/TrackedPerson in the package as2_swarm_person_interfaces.
typedef struct as2_swarm_person_interfaces__msg__TrackedPerson
{
  std_msgs__msg__Header header;
  int32_t id;
  rosidl_runtime_c__String source;
  geometry_msgs__msg__PoseWithCovariance pose;
  float confidence;
} as2_swarm_person_interfaces__msg__TrackedPerson;

// Struct for a sequence of as2_swarm_person_interfaces__msg__TrackedPerson.
typedef struct as2_swarm_person_interfaces__msg__TrackedPerson__Sequence
{
  as2_swarm_person_interfaces__msg__TrackedPerson * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} as2_swarm_person_interfaces__msg__TrackedPerson__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__STRUCT_H_

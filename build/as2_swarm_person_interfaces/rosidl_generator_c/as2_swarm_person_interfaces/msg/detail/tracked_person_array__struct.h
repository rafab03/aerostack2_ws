// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from as2_swarm_person_interfaces:msg/TrackedPersonArray.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__STRUCT_H_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__STRUCT_H_

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
// Member 'persons'
#include "as2_swarm_person_interfaces/msg/detail/tracked_person__struct.h"

/// Struct defined in msg/TrackedPersonArray in the package as2_swarm_person_interfaces.
typedef struct as2_swarm_person_interfaces__msg__TrackedPersonArray
{
  std_msgs__msg__Header header;
  as2_swarm_person_interfaces__msg__TrackedPerson__Sequence persons;
} as2_swarm_person_interfaces__msg__TrackedPersonArray;

// Struct for a sequence of as2_swarm_person_interfaces__msg__TrackedPersonArray.
typedef struct as2_swarm_person_interfaces__msg__TrackedPersonArray__Sequence
{
  as2_swarm_person_interfaces__msg__TrackedPersonArray * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} as2_swarm_person_interfaces__msg__TrackedPersonArray__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__STRUCT_H_

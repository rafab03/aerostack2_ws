// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__rosidl_typesupport_fastrtps_cpp.hpp.em
// with input from as2_swarm_person_interfaces:msg/TrackedPersonArray.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "as2_swarm_person_interfaces/msg/rosidl_typesupport_fastrtps_cpp__visibility_control.h"
#include "as2_swarm_person_interfaces/msg/detail/tracked_person_array__struct.hpp"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

#include "fastcdr/Cdr.h"

namespace as2_swarm_person_interfaces
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_as2_swarm_person_interfaces
cdr_serialize(
  const as2_swarm_person_interfaces::msg::TrackedPersonArray & ros_message,
  eprosima::fastcdr::Cdr & cdr);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_as2_swarm_person_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  as2_swarm_person_interfaces::msg::TrackedPersonArray & ros_message);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_as2_swarm_person_interfaces
get_serialized_size(
  const as2_swarm_person_interfaces::msg::TrackedPersonArray & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_as2_swarm_person_interfaces
max_serialized_size_TrackedPersonArray(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace as2_swarm_person_interfaces

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_as2_swarm_person_interfaces
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, as2_swarm_person_interfaces, msg, TrackedPersonArray)();

#ifdef __cplusplus
}
#endif

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

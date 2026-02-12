// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from as2_swarm_person_interfaces:msg/TrackedPerson.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__TRAITS_HPP_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "as2_swarm_person_interfaces/msg/detail/tracked_person__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__traits.hpp"
// Member 'pose'
#include "geometry_msgs/msg/detail/pose_with_covariance__traits.hpp"

namespace as2_swarm_person_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const TrackedPerson & msg,
  std::ostream & out)
{
  out << "{";
  // member: header
  {
    out << "header: ";
    to_flow_style_yaml(msg.header, out);
    out << ", ";
  }

  // member: id
  {
    out << "id: ";
    rosidl_generator_traits::value_to_yaml(msg.id, out);
    out << ", ";
  }

  // member: source
  {
    out << "source: ";
    rosidl_generator_traits::value_to_yaml(msg.source, out);
    out << ", ";
  }

  // member: pose
  {
    out << "pose: ";
    to_flow_style_yaml(msg.pose, out);
    out << ", ";
  }

  // member: confidence
  {
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const TrackedPerson & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: header
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "header:\n";
    to_block_style_yaml(msg.header, out, indentation + 2);
  }

  // member: id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "id: ";
    rosidl_generator_traits::value_to_yaml(msg.id, out);
    out << "\n";
  }

  // member: source
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "source: ";
    rosidl_generator_traits::value_to_yaml(msg.source, out);
    out << "\n";
  }

  // member: pose
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "pose:\n";
    to_block_style_yaml(msg.pose, out, indentation + 2);
  }

  // member: confidence
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const TrackedPerson & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace as2_swarm_person_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use as2_swarm_person_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const as2_swarm_person_interfaces::msg::TrackedPerson & msg,
  std::ostream & out, size_t indentation = 0)
{
  as2_swarm_person_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use as2_swarm_person_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const as2_swarm_person_interfaces::msg::TrackedPerson & msg)
{
  return as2_swarm_person_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<as2_swarm_person_interfaces::msg::TrackedPerson>()
{
  return "as2_swarm_person_interfaces::msg::TrackedPerson";
}

template<>
inline const char * name<as2_swarm_person_interfaces::msg::TrackedPerson>()
{
  return "as2_swarm_person_interfaces/msg/TrackedPerson";
}

template<>
struct has_fixed_size<as2_swarm_person_interfaces::msg::TrackedPerson>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<as2_swarm_person_interfaces::msg::TrackedPerson>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<as2_swarm_person_interfaces::msg::TrackedPerson>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__TRAITS_HPP_

// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from as2_swarm_person_interfaces:msg/TrackedPersonArray.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__BUILDER_HPP_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "as2_swarm_person_interfaces/msg/detail/tracked_person_array__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace as2_swarm_person_interfaces
{

namespace msg
{

namespace builder
{

class Init_TrackedPersonArray_persons
{
public:
  explicit Init_TrackedPersonArray_persons(::as2_swarm_person_interfaces::msg::TrackedPersonArray & msg)
  : msg_(msg)
  {}
  ::as2_swarm_person_interfaces::msg::TrackedPersonArray persons(::as2_swarm_person_interfaces::msg::TrackedPersonArray::_persons_type arg)
  {
    msg_.persons = std::move(arg);
    return std::move(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPersonArray msg_;
};

class Init_TrackedPersonArray_header
{
public:
  Init_TrackedPersonArray_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_TrackedPersonArray_persons header(::as2_swarm_person_interfaces::msg::TrackedPersonArray::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_TrackedPersonArray_persons(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPersonArray msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::as2_swarm_person_interfaces::msg::TrackedPersonArray>()
{
  return as2_swarm_person_interfaces::msg::builder::Init_TrackedPersonArray_header();
}

}  // namespace as2_swarm_person_interfaces

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__BUILDER_HPP_

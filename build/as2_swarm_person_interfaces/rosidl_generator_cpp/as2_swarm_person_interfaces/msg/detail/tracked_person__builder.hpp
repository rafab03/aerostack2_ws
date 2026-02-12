// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from as2_swarm_person_interfaces:msg/TrackedPerson.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__BUILDER_HPP_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "as2_swarm_person_interfaces/msg/detail/tracked_person__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace as2_swarm_person_interfaces
{

namespace msg
{

namespace builder
{

class Init_TrackedPerson_confidence
{
public:
  explicit Init_TrackedPerson_confidence(::as2_swarm_person_interfaces::msg::TrackedPerson & msg)
  : msg_(msg)
  {}
  ::as2_swarm_person_interfaces::msg::TrackedPerson confidence(::as2_swarm_person_interfaces::msg::TrackedPerson::_confidence_type arg)
  {
    msg_.confidence = std::move(arg);
    return std::move(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPerson msg_;
};

class Init_TrackedPerson_pose
{
public:
  explicit Init_TrackedPerson_pose(::as2_swarm_person_interfaces::msg::TrackedPerson & msg)
  : msg_(msg)
  {}
  Init_TrackedPerson_confidence pose(::as2_swarm_person_interfaces::msg::TrackedPerson::_pose_type arg)
  {
    msg_.pose = std::move(arg);
    return Init_TrackedPerson_confidence(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPerson msg_;
};

class Init_TrackedPerson_source
{
public:
  explicit Init_TrackedPerson_source(::as2_swarm_person_interfaces::msg::TrackedPerson & msg)
  : msg_(msg)
  {}
  Init_TrackedPerson_pose source(::as2_swarm_person_interfaces::msg::TrackedPerson::_source_type arg)
  {
    msg_.source = std::move(arg);
    return Init_TrackedPerson_pose(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPerson msg_;
};

class Init_TrackedPerson_id
{
public:
  explicit Init_TrackedPerson_id(::as2_swarm_person_interfaces::msg::TrackedPerson & msg)
  : msg_(msg)
  {}
  Init_TrackedPerson_source id(::as2_swarm_person_interfaces::msg::TrackedPerson::_id_type arg)
  {
    msg_.id = std::move(arg);
    return Init_TrackedPerson_source(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPerson msg_;
};

class Init_TrackedPerson_header
{
public:
  Init_TrackedPerson_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_TrackedPerson_id header(::as2_swarm_person_interfaces::msg::TrackedPerson::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_TrackedPerson_id(msg_);
  }

private:
  ::as2_swarm_person_interfaces::msg::TrackedPerson msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::as2_swarm_person_interfaces::msg::TrackedPerson>()
{
  return as2_swarm_person_interfaces::msg::builder::Init_TrackedPerson_header();
}

}  // namespace as2_swarm_person_interfaces

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__BUILDER_HPP_

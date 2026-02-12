// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from as2_swarm_person_interfaces:msg/TrackedPerson.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__STRUCT_HPP_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.hpp"
// Member 'pose'
#include "geometry_msgs/msg/detail/pose_with_covariance__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPerson __attribute__((deprecated))
#else
# define DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPerson __declspec(deprecated)
#endif

namespace as2_swarm_person_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct TrackedPerson_
{
  using Type = TrackedPerson_<ContainerAllocator>;

  explicit TrackedPerson_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_init),
    pose(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->id = 0l;
      this->source = "";
      this->confidence = 0.0f;
    }
  }

  explicit TrackedPerson_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_alloc, _init),
    source(_alloc),
    pose(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->id = 0l;
      this->source = "";
      this->confidence = 0.0f;
    }
  }

  // field types and members
  using _header_type =
    std_msgs::msg::Header_<ContainerAllocator>;
  _header_type header;
  using _id_type =
    int32_t;
  _id_type id;
  using _source_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _source_type source;
  using _pose_type =
    geometry_msgs::msg::PoseWithCovariance_<ContainerAllocator>;
  _pose_type pose;
  using _confidence_type =
    float;
  _confidence_type confidence;

  // setters for named parameter idiom
  Type & set__header(
    const std_msgs::msg::Header_<ContainerAllocator> & _arg)
  {
    this->header = _arg;
    return *this;
  }
  Type & set__id(
    const int32_t & _arg)
  {
    this->id = _arg;
    return *this;
  }
  Type & set__source(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->source = _arg;
    return *this;
  }
  Type & set__pose(
    const geometry_msgs::msg::PoseWithCovariance_<ContainerAllocator> & _arg)
  {
    this->pose = _arg;
    return *this;
  }
  Type & set__confidence(
    const float & _arg)
  {
    this->confidence = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator> *;
  using ConstRawPtr =
    const as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPerson
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPerson
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const TrackedPerson_ & other) const
  {
    if (this->header != other.header) {
      return false;
    }
    if (this->id != other.id) {
      return false;
    }
    if (this->source != other.source) {
      return false;
    }
    if (this->pose != other.pose) {
      return false;
    }
    if (this->confidence != other.confidence) {
      return false;
    }
    return true;
  }
  bool operator!=(const TrackedPerson_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct TrackedPerson_

// alias to use template instance with default allocator
using TrackedPerson =
  as2_swarm_person_interfaces::msg::TrackedPerson_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace as2_swarm_person_interfaces

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON__STRUCT_HPP_

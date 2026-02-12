// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from as2_swarm_person_interfaces:msg/TrackedPersonArray.idl
// generated code does not contain a copyright notice

#ifndef AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__STRUCT_HPP_
#define AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__STRUCT_HPP_

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
// Member 'persons'
#include "as2_swarm_person_interfaces/msg/detail/tracked_person__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPersonArray __attribute__((deprecated))
#else
# define DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPersonArray __declspec(deprecated)
#endif

namespace as2_swarm_person_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct TrackedPersonArray_
{
  using Type = TrackedPersonArray_<ContainerAllocator>;

  explicit TrackedPersonArray_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_init)
  {
    (void)_init;
  }

  explicit TrackedPersonArray_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _header_type =
    std_msgs::msg::Header_<ContainerAllocator>;
  _header_type header;
  using _persons_type =
    std::vector<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>>;
  _persons_type persons;

  // setters for named parameter idiom
  Type & set__header(
    const std_msgs::msg::Header_<ContainerAllocator> & _arg)
  {
    this->header = _arg;
    return *this;
  }
  Type & set__persons(
    const std::vector<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<as2_swarm_person_interfaces::msg::TrackedPerson_<ContainerAllocator>>> & _arg)
  {
    this->persons = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator> *;
  using ConstRawPtr =
    const as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPersonArray
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__as2_swarm_person_interfaces__msg__TrackedPersonArray
    std::shared_ptr<as2_swarm_person_interfaces::msg::TrackedPersonArray_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const TrackedPersonArray_ & other) const
  {
    if (this->header != other.header) {
      return false;
    }
    if (this->persons != other.persons) {
      return false;
    }
    return true;
  }
  bool operator!=(const TrackedPersonArray_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct TrackedPersonArray_

// alias to use template instance with default allocator
using TrackedPersonArray =
  as2_swarm_person_interfaces::msg::TrackedPersonArray_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace as2_swarm_person_interfaces

#endif  // AS2_SWARM_PERSON_INTERFACES__MSG__DETAIL__TRACKED_PERSON_ARRAY__STRUCT_HPP_

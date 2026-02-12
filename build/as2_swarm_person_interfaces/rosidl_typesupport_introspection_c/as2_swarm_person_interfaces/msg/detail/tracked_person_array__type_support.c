// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from as2_swarm_person_interfaces:msg/TrackedPersonArray.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "as2_swarm_person_interfaces/msg/detail/tracked_person_array__rosidl_typesupport_introspection_c.h"
#include "as2_swarm_person_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "as2_swarm_person_interfaces/msg/detail/tracked_person_array__functions.h"
#include "as2_swarm_person_interfaces/msg/detail/tracked_person_array__struct.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/header.h"
// Member `header`
#include "std_msgs/msg/detail/header__rosidl_typesupport_introspection_c.h"
// Member `persons`
#include "as2_swarm_person_interfaces/msg/tracked_person.h"
// Member `persons`
#include "as2_swarm_person_interfaces/msg/detail/tracked_person__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  as2_swarm_person_interfaces__msg__TrackedPersonArray__init(message_memory);
}

void as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_fini_function(void * message_memory)
{
  as2_swarm_person_interfaces__msg__TrackedPersonArray__fini(message_memory);
}

size_t as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__size_function__TrackedPersonArray__persons(
  const void * untyped_member)
{
  const as2_swarm_person_interfaces__msg__TrackedPerson__Sequence * member =
    (const as2_swarm_person_interfaces__msg__TrackedPerson__Sequence *)(untyped_member);
  return member->size;
}

const void * as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__get_const_function__TrackedPersonArray__persons(
  const void * untyped_member, size_t index)
{
  const as2_swarm_person_interfaces__msg__TrackedPerson__Sequence * member =
    (const as2_swarm_person_interfaces__msg__TrackedPerson__Sequence *)(untyped_member);
  return &member->data[index];
}

void * as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__get_function__TrackedPersonArray__persons(
  void * untyped_member, size_t index)
{
  as2_swarm_person_interfaces__msg__TrackedPerson__Sequence * member =
    (as2_swarm_person_interfaces__msg__TrackedPerson__Sequence *)(untyped_member);
  return &member->data[index];
}

void as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__fetch_function__TrackedPersonArray__persons(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const as2_swarm_person_interfaces__msg__TrackedPerson * item =
    ((const as2_swarm_person_interfaces__msg__TrackedPerson *)
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__get_const_function__TrackedPersonArray__persons(untyped_member, index));
  as2_swarm_person_interfaces__msg__TrackedPerson * value =
    (as2_swarm_person_interfaces__msg__TrackedPerson *)(untyped_value);
  *value = *item;
}

void as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__assign_function__TrackedPersonArray__persons(
  void * untyped_member, size_t index, const void * untyped_value)
{
  as2_swarm_person_interfaces__msg__TrackedPerson * item =
    ((as2_swarm_person_interfaces__msg__TrackedPerson *)
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__get_function__TrackedPersonArray__persons(untyped_member, index));
  const as2_swarm_person_interfaces__msg__TrackedPerson * value =
    (const as2_swarm_person_interfaces__msg__TrackedPerson *)(untyped_value);
  *item = *value;
}

bool as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__resize_function__TrackedPersonArray__persons(
  void * untyped_member, size_t size)
{
  as2_swarm_person_interfaces__msg__TrackedPerson__Sequence * member =
    (as2_swarm_person_interfaces__msg__TrackedPerson__Sequence *)(untyped_member);
  as2_swarm_person_interfaces__msg__TrackedPerson__Sequence__fini(member);
  return as2_swarm_person_interfaces__msg__TrackedPerson__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_member_array[2] = {
  {
    "header",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(as2_swarm_person_interfaces__msg__TrackedPersonArray, header),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "persons",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(as2_swarm_person_interfaces__msg__TrackedPersonArray, persons),  // bytes offset in struct
    NULL,  // default value
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__size_function__TrackedPersonArray__persons,  // size() function pointer
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__get_const_function__TrackedPersonArray__persons,  // get_const(index) function pointer
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__get_function__TrackedPersonArray__persons,  // get(index) function pointer
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__fetch_function__TrackedPersonArray__persons,  // fetch(index, &value) function pointer
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__assign_function__TrackedPersonArray__persons,  // assign(index, value) function pointer
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__resize_function__TrackedPersonArray__persons  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_members = {
  "as2_swarm_person_interfaces__msg",  // message namespace
  "TrackedPersonArray",  // message name
  2,  // number of fields
  sizeof(as2_swarm_person_interfaces__msg__TrackedPersonArray),
  as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_member_array,  // message members
  as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_init_function,  // function to initialize message memory (memory has to be allocated)
  as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_type_support_handle = {
  0,
  &as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_as2_swarm_person_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, as2_swarm_person_interfaces, msg, TrackedPersonArray)() {
  as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, std_msgs, msg, Header)();
  as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_member_array[1].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, as2_swarm_person_interfaces, msg, TrackedPerson)();
  if (!as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_type_support_handle.typesupport_identifier) {
    as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &as2_swarm_person_interfaces__msg__TrackedPersonArray__rosidl_typesupport_introspection_c__TrackedPersonArray_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

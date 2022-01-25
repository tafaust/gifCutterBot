from enum import Enum


class TaskState(Enum):
    # static states:
    # a task can either succeed or fail
    VALID = 0x0
    INVALID = 0x1
    # actionable states
    DROP = 0x10
    DONE = 0x99


class TaskConfigState(Enum):
    VALID = 0x0
    INVALID = 0x1

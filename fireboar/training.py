from __future__ import annotations
import re
import uuid
import json
import datetime
from enum import StrEnum
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


class ExerciseType(StrEnum):
    NORMAL = "NORMAL"
    INTERVAL = "INTERVAL"

@dataclass_json
@dataclass(slots=True)
class IntervalConfig:
    intervals: int = 1
    working_time: int = 15
    rest_time: int = 15

    def set_intervals(self, v: str):
        value = 1
        try:
            value = int(v.strip() or 1)
        except ValueError:
            pass

        self.intervals = value

    def set_working_time(self, v: str):
        value = 15
        try:
            value = int(v.strip() or 15)
        except ValueError:
            pass

        self.working_time = value

    def set_rest_time(self, v: str):
        value = 15
        try:
            value = int(v.strip() or 15)
        except ValueError:
            pass

        self.rest_time = value


@dataclass_json
@dataclass(slots=True)
class Exercise:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    sets: int = 3
    suggested_weight: str = ""
    suggested_reps: str = "8 - 10"
    rest_seconds: int = 60
    superset_id: str = ""
    type: ExerciseType = ExerciseType.NORMAL
    interval_config: IntervalConfig = field(default_factory=IntervalConfig)

    def set_name(self, name: str, header):
        self.name = name.strip()
        header.value = name.strip()

    def set_sets(self, sets: str):
        value = 1
        try:
            value = int(set.strip() or 1)
        except ValueError:
            pass

        self.sets = value

    def set_weight(self, weight: str):
        self.suggested_weight = weight.strip()

    def set_reps(self, reps: str):
        self.suggested_reps = reps.strip()

    def set_rest(self, rest: str):
        value = 60
        try:
            value = int(rest.strip() or 60)
        except ValueError:
            pass

        self.rest_seconds = value

    def set_superset(self, id: str):
        self.superset_id = id.strip()


class TrainingAction(StrEnum):
    REST = "REST"
    SUMMARY = "SUMMARY"
    INTERVAL_WORK = "INTERVAL_WORK"


@dataclass_json
@dataclass(slots=True)
class SessionSet:
    exercise: Exercise | None = None
    id: str | None = None
    name: str | None = None
    weight: str = ""
    reps: str | int = ""
    notes: str = ""
    set_index: int = 0

    def get_name(self) -> str:
        if self.exercise:
            return self.exercise.name or ""
        return self.name or self.id or ""

    def get_id(self) -> str:
        if self.exercise:
            return self.exercise.id or ""
        return self.id or ""

    def get_header(self) -> list[str]:
        if not self.exercise:
            return ""

        if not self.exercise.superset_id.strip():
            superset_string = ""
        else:
            superset_string = f"Superseria {self.exercise.superset_id}: "

        return [
            f"{superset_string}{self.get_name()} – seria {self.set_index}/{self.exercise.sets}",
            f"📔 Proponowane {self.exercise.suggested_weight} x {self.exercise.suggested_reps}",
        ]

    def get_last_info(self) -> str:
        return f"⌚ Ostatnio: {self.weight} x {self.reps} ({self.notes})"

    def get_action_list(self) -> list[TrainingAction]:
        return [TrainingAction.SUMMARY, TrainingAction.REST]


@dataclass_json
@dataclass(slots=True)
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    training: str = ""
    sets: list[SessionSet] = field(default_factory=list)

    def get_date(self) -> str:
        return str(datetime.datetime.fromtimestamp(self.date)).split(' ')[0]


@dataclass_json
@dataclass(slots=True)
class Training:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    exercises: list[Exercise] = field(default_factory=list)

    def get_sets_list(self) -> list[SessionSet]:
        sets = []
        supersets = {}
        for ex in self.exercises:
            if ex.superset_id.strip():
                supersets.setdefault(ex.superset_id.strip(), []).append(
                    ex
                )

        superset_visited = set()
        for ex in self.exercises:
            s_id = ex.superset_id.strip()
            if not s_id:
                for i in range(ex.sets):
                    sets.append(
                        SessionSet(
                            exercise=ex,
                            set_index=i + 1,
                        )
                    )
            else:
                if s_id in superset_visited:
                    continue

                max_sets = max(ex.sets for ex in supersets[s_id])
                for i in range(max_sets):
                    for super_ex in supersets[s_id]:
                        if i >= super_ex.sets:
                            continue
                        sets.append(
                            SessionSet(
                                exercise=ex,
                                set_index=i + 1
                            )
                        )

                superset_visited.add(s_id)
        return sets

    def get_sessions(self, sessions) -> list[Session]:
        return [s for s in sessions if s.training == self.id]

    def add_exercise(self):
        self.exercises.append(Exercise())

    def remove_exercise(self, id: str):
        self.exercises = [ex for ex in self.exercises if ex.id != id]

    def move_exercise_down(self, ex_id: str):
        exercise_idx = len(self.exercises)
        for i in range(len(self.exercises)):
            if self.exercises[i].id == ex_id:
                exercise_idx = i
        if exercise_idx > len(self.exercises) - 2:
            return

        exercise_after = self.exercises[exercise_idx + 1]
        self.exercises[exercise_idx + 1] = self.exercises[exercise_idx]
        self.exercises[exercise_idx] = exercise_after

    def move_exercise_up(self, ex_id: str):
        exercise_idx = -1
        for i in range(len(self.exercises)):
            if self.exercises[i].id == ex_id:
                exercise_idx = i
        if exercise_idx < 1:
            return

        exercise_before = self.exercises[exercise_idx - 1]
        self.exercises[exercise_idx - 1] = self.exercises[exercise_idx]
        self.exercises[exercise_idx] = exercise_before


@dataclass_json
@dataclass(slots=True)
class PersonalBest:
    exercise_id: str
    max_weight: int | str
    max_reps: int | str
    session_date: str

    @staticmethod
    def get_pb_for_training(sessions: list[Session], exercise_id: str) -> PersonalBest | None:
        max_weight = 0.0
        max_reps = 0
        session_date = None
        if not sessions:
            return None

        for s in sessions:
            for set in s.sets:
                if set.get_id() != exercise_id:
                    continue
                w = normalize_string(set.weight)
                r = int(normalize_string(set.reps))
                if w > max_weight:
                    max_weight = w
                    max_reps = r
                    session_date = s.get_date()
                if w == max_weight and r > max_reps:
                    max_reps = r
                    session_date = s.get_date()

        if not session_date:
            return None

        return PersonalBest(
            exercise_id=exercise_id,
            max_weight=max_weight,
            max_reps=max_reps,
            session_date=session_date,
        )

    def get_str(self) -> str:
        return f"🥇 Twój max: {self.max_weight} kg x {self.max_reps} ({self.session_date})"


def normalize_string(value: str | int | float) -> float:
    if isinstance(value, int) or isinstance(value, float):
        return float(value)

    cleaned = re.sub(r"[^0-9.,]", "", value)
    cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def get_session_pb_emoji(sessions: list, session_idx: int) -> str:
    # TODO - get this
    current_pb = "🥇"    
    historical_pb = "🥈"

    #for s in sessions:
    #    if s["sets"]

    return ""



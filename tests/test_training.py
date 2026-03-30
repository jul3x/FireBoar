"""
Unit tests for weight/reps suggestion logic in fireboar.training.
Focus: Exercise.get_set_weight, get_set_reps, get_set_rest,
       SessionSet.get_suggestions, Training.get_sets_list,
       PersonalBest.get_pb_for_training, advanced sets management.
"""
import datetime
import pytest
from fireboar.training import (
    Exercise, ExerciseSet, ExerciseType, IntervalConfig,
    Session, SessionSet, Training, PersonalBest, Progression,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_exercise(
    name="Squat",
    sets=3,
    suggested_weight="100",
    suggested_reps="8 - 10",
    rest_seconds=90,
    superset_id="",
    exercise_sets=None,
):
    ex = Exercise()
    ex.name = name
    ex.sets = sets
    ex.suggested_weight = suggested_weight
    ex.suggested_reps = suggested_reps
    ex.rest_seconds = rest_seconds
    ex.superset_id = superset_id
    if exercise_sets is not None:
        ex.exercise_sets = exercise_sets
    return ex


def make_session_set(exercise, set_index, weight="", reps=""):
    return SessionSet(exercise=exercise, set_index=set_index, weight=weight, reps=reps)


def make_session(training_id, sets):
    s = Session()
    s.training = training_id
    s.sets = sets
    return s


# ---------------------------------------------------------------------------
# Exercise.get_set_weight — simple (no advanced sets)
# ---------------------------------------------------------------------------

class TestGetSetWeightSimple:
    def test_returns_global_weight_for_set1(self):
        ex = make_exercise(suggested_weight="80")
        assert ex.get_set_weight(1) == "80"

    def test_returns_global_weight_for_set2(self):
        ex = make_exercise(suggested_weight="80")
        assert ex.get_set_weight(2) == "80"

    def test_returns_global_weight_for_set3(self):
        ex = make_exercise(suggested_weight="80")
        assert ex.get_set_weight(3) == "80"

    def test_set_index_zero_returns_global(self):
        # set_index=0 is below valid range (>0 required), fallback to global
        ex = make_exercise(suggested_weight="80")
        assert ex.get_set_weight(0) == "80"

    def test_empty_weight(self):
        ex = make_exercise(suggested_weight="")
        assert ex.get_set_weight(1) == ""

    def test_large_set_index_returns_global(self):
        ex = make_exercise(suggested_weight="50", sets=3)
        assert ex.get_set_weight(99) == "50"


# ---------------------------------------------------------------------------
# Exercise.get_set_reps — simple (no advanced sets)
# ---------------------------------------------------------------------------

class TestGetSetRepsSimple:
    def test_returns_global_reps_for_set1(self):
        ex = make_exercise(suggested_reps="8 - 10")
        assert ex.get_set_reps(1) == "8 - 10"

    def test_set_index_zero_returns_global(self):
        ex = make_exercise(suggested_reps="5")
        assert ex.get_set_reps(0) == "5"

    def test_empty_reps(self):
        ex = make_exercise(suggested_reps="")
        assert ex.get_set_reps(1) == ""

    def test_large_set_index_returns_global(self):
        ex = make_exercise(suggested_reps="12", sets=3)
        assert ex.get_set_reps(99) == "12"


# ---------------------------------------------------------------------------
# Exercise.get_set_rest — simple
# ---------------------------------------------------------------------------

class TestGetSetRestSimple:
    def test_returns_global_rest(self):
        ex = make_exercise(rest_seconds=120)
        assert ex.get_set_rest(1) == 120

    def test_set_index_zero_returns_global(self):
        ex = make_exercise(rest_seconds=60)
        assert ex.get_set_rest(0) == 60


# ---------------------------------------------------------------------------
# Exercise.get_set_weight / reps / rest — advanced sets
# ---------------------------------------------------------------------------

class TestGetSetWeightAdvanced:
    def _ex_with_sets(self):
        ex = make_exercise(suggested_weight="100", suggested_reps="8", rest_seconds=90, sets=3)
        ex.exercise_sets = [
            ExerciseSet(suggested_weight="60",  suggested_reps="12", rest_seconds=60),
            ExerciseSet(suggested_weight="80",  suggested_reps="10", rest_seconds=75),
            ExerciseSet(suggested_weight="100", suggested_reps="8",  rest_seconds=90),
        ]
        return ex

    def test_set1_weight(self):
        assert self._ex_with_sets().get_set_weight(1) == "60"

    def test_set2_weight(self):
        assert self._ex_with_sets().get_set_weight(2) == "80"

    def test_set3_weight(self):
        assert self._ex_with_sets().get_set_weight(3) == "100"

    def test_set1_reps(self):
        assert self._ex_with_sets().get_set_reps(1) == "12"

    def test_set2_reps(self):
        assert self._ex_with_sets().get_set_reps(2) == "10"

    def test_set3_reps(self):
        assert self._ex_with_sets().get_set_reps(3) == "8"

    def test_set1_rest(self):
        assert self._ex_with_sets().get_set_rest(1) == 60

    def test_set2_rest(self):
        assert self._ex_with_sets().get_set_rest(2) == 75

    def test_set3_rest(self):
        assert self._ex_with_sets().get_set_rest(3) == 90

    def test_set_index_zero_falls_back_to_global(self):
        # 0 is not > 0, so falls back to global
        ex = self._ex_with_sets()
        assert ex.get_set_weight(0) == "100"
        assert ex.get_set_reps(0) == "8"
        assert ex.get_set_rest(0) == 90

    def test_set_index_above_count_falls_back_to_global(self):
        # set_index=4 > len(exercise_sets)=3
        ex = self._ex_with_sets()
        assert ex.get_set_weight(4) == "100"
        assert ex.get_set_reps(4) == "8"
        assert ex.get_set_rest(4) == 90

    def test_empty_per_set_weight_returned_as_is(self):
        ex = make_exercise(suggested_weight="100", sets=1)
        ex.exercise_sets = [ExerciseSet(suggested_weight="", suggested_reps="5")]
        assert ex.get_set_weight(1) == ""

    def test_different_weight_each_set(self):
        ex = make_exercise(suggested_weight="0", sets=5)
        weights = ["20", "40", "60", "80", "100"]
        ex.exercise_sets = [ExerciseSet(suggested_weight=w) for w in weights]
        for i, w in enumerate(weights, start=1):
            assert ex.get_set_weight(i) == w


# ---------------------------------------------------------------------------
# SessionSet.get_suggestions
# ---------------------------------------------------------------------------

class TestGetSuggestions:
    def test_normal_weight_and_reps(self):
        ex = make_exercise(suggested_weight="80", suggested_reps="8 - 10")
        ss = make_session_set(ex, set_index=1)
        assert ss.get_suggestions() == "📔 Proponowane 80 x 8 - 10"

    def test_empty_weight_shows_pusto(self):
        ex = make_exercise(suggested_weight="", suggested_reps="10")
        ss = make_session_set(ex, set_index=1)
        assert ss.get_suggestions() == "📔 Proponowane pusto x 10"

    def test_empty_reps_shows_1(self):
        ex = make_exercise(suggested_weight="60", suggested_reps="")
        ss = make_session_set(ex, set_index=1)
        assert ss.get_suggestions() == "📔 Proponowane 60 x 1"

    def test_both_empty(self):
        ex = make_exercise(suggested_weight="", suggested_reps="")
        ss = make_session_set(ex, set_index=1)
        assert ss.get_suggestions() == "📔 Proponowane pusto x 1"

    def test_advanced_set_uses_per_set_weight(self):
        ex = make_exercise(suggested_weight="100", suggested_reps="5", sets=3)
        ex.exercise_sets = [
            ExerciseSet(suggested_weight="70", suggested_reps="12"),
            ExerciseSet(suggested_weight="85", suggested_reps="10"),
            ExerciseSet(suggested_weight="100", suggested_reps="8"),
        ]
        ss1 = make_session_set(ex, set_index=1)
        ss2 = make_session_set(ex, set_index=2)
        ss3 = make_session_set(ex, set_index=3)
        assert ss1.get_suggestions() == "📔 Proponowane 70 x 12"
        assert ss2.get_suggestions() == "📔 Proponowane 85 x 10"
        assert ss3.get_suggestions() == "📔 Proponowane 100 x 8"


# ---------------------------------------------------------------------------
# Training.get_sets_list — normal (no supersets)
# ---------------------------------------------------------------------------

class TestGetSetsListNormal:
    def test_single_exercise_three_sets(self):
        t = Training()
        ex = make_exercise(name="Bench Press", sets=3)
        t.exercises = [ex]
        sets = t.get_sets_list()
        assert len(sets) == 3
        assert all(s.exercise == ex for s in sets)
        assert [s.set_index for s in sets] == [1, 2, 3]

    def test_two_exercises(self):
        t = Training()
        ex1 = make_exercise(name="Squat", sets=4)
        ex2 = make_exercise(name="OHP", sets=2)
        t.exercises = [ex1, ex2]
        sets = t.get_sets_list()
        assert len(sets) == 6
        assert [s.exercise.name for s in sets] == ["Squat"] * 4 + ["OHP"] * 2
        assert [s.set_index for s in sets] == [1, 2, 3, 4, 1, 2]

    def test_single_set_exercise(self):
        t = Training()
        ex = make_exercise(sets=1)
        t.exercises = [ex]
        sets = t.get_sets_list()
        assert len(sets) == 1
        assert sets[0].set_index == 1

    def test_empty_training(self):
        t = Training()
        t.exercises = []
        assert t.get_sets_list() == []

    def test_set_index_starts_at_1(self):
        t = Training()
        t.exercises = [make_exercise(sets=5)]
        sets = t.get_sets_list()
        assert sets[0].set_index == 1
        assert sets[4].set_index == 5


# ---------------------------------------------------------------------------
# Training.get_sets_list — supersets
# ---------------------------------------------------------------------------

class TestGetSetsListSupersets:
    def test_two_exercises_in_superset_interleaved(self):
        t = Training()
        ex1 = make_exercise(name="Curl", sets=3, superset_id="A")
        ex2 = make_exercise(name="Tricep", sets=3, superset_id="A")
        t.exercises = [ex1, ex2]
        sets = t.get_sets_list()
        # Expect: Curl1, Tricep1, Curl2, Tricep2, Curl3, Tricep3
        assert len(sets) == 6
        names = [s.exercise.name for s in sets]
        assert names == ["Curl", "Tricep", "Curl", "Tricep", "Curl", "Tricep"]
        indexes = [s.set_index for s in sets]
        assert indexes == [1, 1, 2, 2, 3, 3]

    def test_superset_unequal_sets(self):
        # ex1 has 3 sets, ex2 has 2 sets — ex2 is skipped for set 3
        t = Training()
        ex1 = make_exercise(name="A", sets=3, superset_id="X")
        ex2 = make_exercise(name="B", sets=2, superset_id="X")
        t.exercises = [ex1, ex2]
        sets = t.get_sets_list()
        names = [s.exercise.name for s in sets]
        # Round 1: A1, B1 | Round 2: A2, B2 | Round 3: A3 (B has no set 3)
        assert names == ["A", "B", "A", "B", "A"]
        assert [s.set_index for s in sets] == [1, 1, 2, 2, 3]

    def test_mixed_superset_and_normal(self):
        t = Training()
        ex_normal = make_exercise(name="Squat", sets=3, superset_id="")
        ex_s1 = make_exercise(name="Curl", sets=2, superset_id="A")
        ex_s2 = make_exercise(name="Tricep", sets=2, superset_id="A")
        t.exercises = [ex_normal, ex_s1, ex_s2]
        sets = t.get_sets_list()
        names = [s.exercise.name for s in sets]
        # Squat×3, then Curl/Tricep interleaved ×2
        assert names == ["Squat", "Squat", "Squat", "Curl", "Tricep", "Curl", "Tricep"]

    def test_three_exercises_in_superset(self):
        t = Training()
        ex1 = make_exercise(name="A", sets=2, superset_id="S")
        ex2 = make_exercise(name="B", sets=2, superset_id="S")
        ex3 = make_exercise(name="C", sets=2, superset_id="S")
        t.exercises = [ex1, ex2, ex3]
        sets = t.get_sets_list()
        names = [s.exercise.name for s in sets]
        assert names == ["A", "B", "C", "A", "B", "C"]


# ---------------------------------------------------------------------------
# Exercise advanced sets management
# ---------------------------------------------------------------------------

class TestAdvancedSetsManagement:
    def test_enable_advanced_sets_creates_correct_count(self):
        ex = make_exercise(sets=4, suggested_weight="60", suggested_reps="10", rest_seconds=60)
        ex.enable_advanced_sets()
        assert len(ex.exercise_sets) == 4

    def test_enable_advanced_sets_copies_global_values(self):
        ex = make_exercise(sets=3, suggested_weight="70", suggested_reps="8", rest_seconds=90)
        ex.enable_advanced_sets()
        for s in ex.exercise_sets:
            assert s.suggested_weight == "70"
            assert s.suggested_reps == "8"
            assert s.rest_seconds == 90

    def test_is_advanced_true_after_enable(self):
        ex = make_exercise(sets=2)
        ex.enable_advanced_sets()
        assert ex.is_advanced() is True

    def test_is_advanced_false_by_default(self):
        ex = make_exercise()
        assert ex.is_advanced() is False

    def test_disable_advanced_sets(self):
        ex = make_exercise(sets=3)
        ex.enable_advanced_sets()
        ex.disable_advanced_sets()
        assert ex.exercise_sets == []
        assert ex.is_advanced() is False

    def test_sync_advanced_sets_count_grows(self):
        ex = make_exercise(sets=2, suggested_weight="50", suggested_reps="5")
        ex.enable_advanced_sets()
        ex.sets = 4
        ex.sync_advanced_sets_count()
        assert len(ex.exercise_sets) == 4
        # New sets inherit global defaults
        assert ex.exercise_sets[2].suggested_weight == "50"
        assert ex.exercise_sets[3].suggested_reps == "5"

    def test_sync_advanced_sets_count_shrinks(self):
        ex = make_exercise(sets=4)
        ex.enable_advanced_sets()
        ex.sets = 2
        ex.sync_advanced_sets_count()
        assert len(ex.exercise_sets) == 2

    def test_sync_advanced_sets_count_no_change(self):
        ex = make_exercise(sets=3)
        ex.enable_advanced_sets()
        ex.sync_advanced_sets_count()
        assert len(ex.exercise_sets) == 3


# ---------------------------------------------------------------------------
# PersonalBest.get_pb_for_training
# ---------------------------------------------------------------------------

class TestPersonalBest:
    def _make_session_with_set(self, ex_id, weight, reps):
        ex = Exercise()
        ex.id = ex_id
        ss = SessionSet(exercise=ex, weight=weight, reps=str(reps))
        s = Session()
        s.sets = [ss]
        return s

    def test_no_sessions_returns_none(self):
        assert PersonalBest.get_pb_for_training([], "any-id") is None

    def test_empty_sessions_returns_none(self):
        s = Session()
        s.sets = []
        assert PersonalBest.get_pb_for_training([s], "any-id") is None

    def test_single_session_returns_pb(self):
        ex_id = "ex-1"
        s = self._make_session_with_set(ex_id, "100", 8)
        pb = PersonalBest.get_pb_for_training([s], ex_id)
        assert pb is not None
        assert pb.max_weight == 100.0
        assert pb.max_reps == 8

    def test_picks_highest_weight(self):
        ex_id = "ex-1"
        s1 = self._make_session_with_set(ex_id, "80", 10)
        s2 = self._make_session_with_set(ex_id, "100", 6)
        s3 = self._make_session_with_set(ex_id, "90", 8)
        pb = PersonalBest.get_pb_for_training([s1, s2, s3], ex_id)
        assert pb.max_weight == 100.0

    def test_same_weight_picks_most_reps(self):
        ex_id = "ex-1"
        s1 = self._make_session_with_set(ex_id, "100", 6)
        s2 = self._make_session_with_set(ex_id, "100", 10)
        s3 = self._make_session_with_set(ex_id, "100", 8)
        pb = PersonalBest.get_pb_for_training([s1, s2, s3], ex_id)
        assert pb.max_reps == 10

    def test_ignores_different_exercise(self):
        ex_id = "ex-1"
        other_id = "ex-2"
        s1 = self._make_session_with_set(other_id, "200", 20)
        s2 = self._make_session_with_set(ex_id, "80", 8)
        pb = PersonalBest.get_pb_for_training([s1, s2], ex_id)
        assert pb.max_weight == 80.0

    def test_no_matching_exercise_returns_none(self):
        s = self._make_session_with_set("ex-other", "100", 8)
        assert PersonalBest.get_pb_for_training([s], "ex-missing") is None

    def test_weight_with_comma(self):
        ex_id = "ex-1"
        s = self._make_session_with_set(ex_id, "102,5", 5)
        pb = PersonalBest.get_pb_for_training([s], ex_id)
        assert pb.max_weight == 102.5

    def test_get_str_format(self):
        ex_id = "ex-1"
        s = self._make_session_with_set(ex_id, "100", 8)
        s.date = datetime.datetime(2025, 1, 15).timestamp()
        pb = PersonalBest.get_pb_for_training([s], ex_id)
        assert "100" in pb.get_str()
        assert "8" in pb.get_str()
        assert "2025-01-15" in pb.get_str()

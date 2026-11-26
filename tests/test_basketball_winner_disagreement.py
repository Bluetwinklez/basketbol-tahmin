from scripts.evaluate_basketball_winner_disagreement import REFERENCE, SWITCH, choices


def test_winner_override_uses_only_predictions_and_preserves_agreement():
    different, p = choices(.4, .6)
    assert different and p == {REFERENCE: [.6, .4], SWITCH: [.4, .6]}
    different, p = choices(.7, .8)
    assert not different and p[REFERENCE] == p[SWITCH]
    different, p = choices(.5, .6)
    assert different and p[REFERENCE] == [.5, .5]

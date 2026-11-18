import unittest
from harnesslab.offline_recipe import offline_recipe


class OfflineRecipeTests(unittest.TestCase):
    def test_recipe_is_pinned_offline_separate_environments_no_exec(self):
        base='python@sha256:'+'a'*64
        recipe=offline_recipe(base)
        self.assertTrue(recipe.startswith('FROM '+base+' AS agent\n'))
        self.assertEqual(recipe.count('RUN --network=none'),4)
        self.assertEqual(recipe.count('--require-hashes'),4)
        self.assertIn('/opt/agent/bin/python -m pip check',recipe)
        self.assertIn('/opt/verifier/bin/python -m pip check',recipe)
        self.assertIn('--no-deps --find-links=/opt/helper-wheelhouse',recipe)
        agent,verifier=recipe.split(' AS verifier\n')
        self.assertNotIn('COPY verifier',agent)
        self.assertIn('COPY verifier-helper/',verifier)
        for bad in ('apt-get','curl ','wget ','https://','ADD ','latest','--privileged'):
            self.assertNotIn(bad,recipe)

    def test_mutable_or_arbitrary_base_refused(self):
        for value in ('python:3.10','python:latest','python@sha256:short','other@sha256:'+'a'*64,None):
            with self.assertRaises(ValueError):offline_recipe(value)

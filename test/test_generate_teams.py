import unittest
from unittest.mock import patch
from src.team_generator.generator import generate_team


class TestGenerateTeam(unittest.TestCase):

    @patch('src.champions.get_chamption_data')
    def test_generate_team_no_repeats(self, mock_get_champion_data):
        # Mock the champion data
        mock_get_champion_data.return_value = {
            'Aatrox': {}, 'Ahri': {}, 'Akali': {}, 'Alistar': {}, 'Amumu': {},
            'Anivia': {}, 'Annie': {}, 'Ashe': {}, 'AurelionSol': {}, 'Azir': {}
        }

        # Generate the teams
        players = ["jonatas", "arthur", "wanis", "loui"]
        teams = generate_team(players)

        red_team = [i["name"] for i in teams['red_team']]
        blue_team = [i["name"] for i in teams['blue_team']]
        print(red_team)
        print(blue_team)

        # Assert no repeated champions in each team
        self.assertEqual(len(red_team), len(set(red_team)))
        self.assertEqual(len(blue_team), len(set(blue_team)))

        # Assert no repeated champions between teams
        self.assertEqual(len(set(red_team).intersection(set(blue_team))), 0)

        self.assertEqual(len(red_team), 4)
        self.assertEqual(len(blue_team), 4)


if __name__ == '__main__':
    unittest.main()

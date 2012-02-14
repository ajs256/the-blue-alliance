import unittest2
import datetime

from google.appengine.ext import db
from google.appengine.ext import testbed

from datafeeds.datafeed_usfirst_teams import DatafeedUsfirstTeams
from models import Team

class TestDatafeedUsfirstTeams(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_urlfetch_stub()
        self.testbed.init_datastore_v3_stub()
        
        self.datafeed = DatafeedUsfirstTeams()
        
        Team(
            key_name = "frc177",
            team_number = 177,
            first_tpid = 61771,
            first_tpid_year = 2012
        ).put()
    
    def tearDown(self):
        self.testbed.deactivate()
    
    def test_getTeamDetails(self):
        team = self.datafeed.getTeamDetails(177)
        
        self.assertEqual(team.name, "UTC Power/Ensign Bickford Aerospace & Defense & South Windsor High School")
        self.assertEqual(team.address, u"South Windsor, CT\xa0 USA")
        self.assertEqual(team.nickname, "Bobcat Robotics")
        self.assertEqual(team.website, "http://www.bobcatrobotics.org")
    
    def test_instantiateTeams(self):
        Team(
          key_name = "frc4409",
          team_number = 4409,
          first_tpid = 0, #should be 74735
          first_tpid_year = 2011
        ).put()
        
        # We can skip 2000 records, paginate, and still get frc4409 and frc4410 in 2012
        self.datafeed.instantiateTeams(skip=2000, year=2012)
        
        # Check new team insertion
        frc4410 = Team.get_by_key_name("frc4410")
        self.assertEqual(frc4410.team_number, 4410)
        self.assertEqual(frc4410.first_tpid, 74193)
        self.assertEqual(frc4410.first_tpid_year, 2012)
        
        # Check old team updating
        frc4409 = Team.get_by_key_name("frc4409")
        self.assertEqual(frc4409.team_number, 4409)
        self.assertEqual(frc4409.first_tpid, 74735)
        self.assertEqual(frc4409.first_tpid_year, 2012)
        

      
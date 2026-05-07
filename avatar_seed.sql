-- TaskQuest avatar_seed.sql
-- Run this in Supabase SQL editor to seed all 30 avatar items and add customization column

-- 1. Add customization column to profiles if it doesn't exist
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS customization jsonb DEFAULT '{"hair":"brown","skin":"medium"}';

-- 2. Seed avatar items for all 6 classes × 5 tiers
INSERT INTO avatar_items (id, name, description, class, tier, unlock_condition, sort_order)
VALUES
  -- Warrior
  ('warrior_t1','Recruit','A fresh warrior just starting out','warrior',1,'complete_1_quest',10),
  ('warrior_t2','Footman','A seasoned footman with plate armor','warrior',2,'complete_10_quests',11),
  ('warrior_t3','Sergeant','A battle-hardened sergeant','warrior',3,'complete_25_quests',12),
  ('warrior_t4','Champion','A champion warrior adorned in gold','warrior',4,'complete_50_quests',13),
  ('warrior_t5','Warlord','A legendary warlord','warrior',5,'complete_100_quests',14),
  -- Mage
  ('mage_t1','Apprentice','A young mage learning the craft','mage',1,'complete_1_quest',20),
  ('mage_t2','Acolyte','An acolyte with arcane robes','mage',2,'complete_10_quests',21),
  ('mage_t3','Conjurer','A skilled conjurer','mage',3,'complete_25_quests',22),
  ('mage_t4','Sorcerer','A powerful sorcerer','mage',4,'complete_50_quests',23),
  ('mage_t5','Archmage','The Archmage supreme','mage',5,'complete_100_quests',24),
  -- Ranger
  ('ranger_t1','Scout','A quick-footed scout','ranger',1,'complete_1_quest',30),
  ('ranger_t2','Hunter','A skilled hunter','ranger',2,'complete_10_quests',31),
  ('ranger_t3','Tracker','A masterful tracker','ranger',3,'complete_25_quests',32),
  ('ranger_t4','Pathfinder','An elite pathfinder','ranger',4,'complete_50_quests',33),
  ('ranger_t5','Wildwarden','The legendary Wildwarden','ranger',5,'complete_100_quests',34),
  -- Cleric
  ('cleric_t1','Initiate','A devout initiate','cleric',1,'complete_1_quest',40),
  ('cleric_t2','Devotee','A faithful devotee','cleric',2,'complete_10_quests',41),
  ('cleric_t3','Priestess','A holy priestess','cleric',3,'complete_25_quests',42),
  ('cleric_t4','Oracle','A divine oracle','cleric',4,'complete_50_quests',43),
  ('cleric_t5','Saint','A blessed saint','cleric',5,'complete_100_quests',44),
  -- Rogue
  ('rogue_t1','Pickpocket','A nimble pickpocket','rogue',1,'complete_1_quest',50),
  ('rogue_t2','Footpad','A stealthy footpad','rogue',2,'complete_10_quests',51),
  ('rogue_t3','Cutpurse','A skilled cutpurse','rogue',3,'complete_25_quests',52),
  ('rogue_t4','Shadowblade','A deadly shadowblade','rogue',4,'complete_50_quests',53),
  ('rogue_t5','Phantom','The legendary Phantom','rogue',5,'complete_100_quests',54),
  -- Bard
  ('bard_t1','Busker','A cheerful street busker','bard',1,'complete_1_quest',60),
  ('bard_t2','Minstrel','A talented minstrel','bard',2,'complete_10_quests',61),
  ('bard_t3','Troubadour','A renowned troubadour','bard',3,'complete_25_quests',62),
  ('bard_t4','Maestro','A masterful maestro','bard',4,'complete_50_quests',63),
  ('bard_t5','Songweaver','The legendary Songweaver','bard',5,'complete_100_quests',64)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  sort_order = EXCLUDED.sort_order;

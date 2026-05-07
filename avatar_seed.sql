-- TaskQuest avatar_seed.sql
-- Run this in Supabase SQL editor to seed all 30 avatar items and add customization column

-- 1. Add customization column to profiles if it doesn't exist
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS customization jsonb DEFAULT '{"hair":"brown","skin":"medium"}';

-- 2. Seed avatar items for all 6 classes × 5 tiers
--    Columns used by the app: id, name, description, is_default, sort_order
INSERT INTO avatar_items (id, name, description, is_default, sort_order)
VALUES
  -- Warrior
  ('warrior_t1','Recruit','A fresh warrior just starting out',true,10),
  ('warrior_t2','Footman','A seasoned footman with plate armor',false,11),
  ('warrior_t3','Sergeant','A battle-hardened sergeant',false,12),
  ('warrior_t4','Champion','A champion warrior adorned in gold',false,13),
  ('warrior_t5','Warlord','A legendary warlord',false,14),
  -- Mage
  ('mage_t1','Apprentice','A young mage learning the craft',false,20),
  ('mage_t2','Acolyte','An acolyte with arcane robes',false,21),
  ('mage_t3','Conjurer','A skilled conjurer',false,22),
  ('mage_t4','Sorcerer','A powerful sorcerer',false,23),
  ('mage_t5','Archmage','The Archmage supreme',false,24),
  -- Ranger
  ('ranger_t1','Scout','A quick-footed scout',false,30),
  ('ranger_t2','Hunter','A skilled hunter',false,31),
  ('ranger_t3','Tracker','A masterful tracker',false,32),
  ('ranger_t4','Pathfinder','An elite pathfinder',false,33),
  ('ranger_t5','Wildwarden','The legendary Wildwarden',false,34),
  -- Cleric
  ('cleric_t1','Initiate','A devout initiate',false,40),
  ('cleric_t2','Devotee','A faithful devotee',false,41),
  ('cleric_t3','Priestess','A holy priestess',false,42),
  ('cleric_t4','Oracle','A divine oracle',false,43),
  ('cleric_t5','Saint','A blessed saint',false,44),
  -- Rogue
  ('rogue_t1','Pickpocket','A nimble pickpocket',false,50),
  ('rogue_t2','Footpad','A stealthy footpad',false,51),
  ('rogue_t3','Cutpurse','A skilled cutpurse',false,52),
  ('rogue_t4','Shadowblade','A deadly shadowblade',false,53),
  ('rogue_t5','Phantom','The legendary Phantom',false,54),
  -- Bard
  ('bard_t1','Busker','A cheerful street busker',false,60),
  ('bard_t2','Minstrel','A talented minstrel',false,61),
  ('bard_t3','Troubadour','A renowned troubadour',false,62),
  ('bard_t4','Maestro','A masterful maestro',false,63),
  ('bard_t5','Songweaver','The legendary Songweaver',false,64)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  is_default = EXCLUDED.is_default,
  sort_order = EXCLUDED.sort_order;

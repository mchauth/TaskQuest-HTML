-- TaskQuest avatar_seed.sql
-- Run this in Supabase SQL editor to seed all 30 avatar items and add customization column

-- 1. Add sprite_key column to avatar_items
ALTER TABLE avatar_items ADD COLUMN IF NOT EXISTS sprite_key text;

-- 2. Add customization column to profiles
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS customization jsonb DEFAULT '{"hair":"brown","skin":"medium"}';

-- 3. Seed avatar items for all 6 classes × 5 tiers
--    id = gen_random_uuid(), sprite_key = "warrior_t1" etc.
INSERT INTO avatar_items (id, name, description, is_default, sort_order, sprite_key)
VALUES
  -- Warrior
  (gen_random_uuid(),'Recruit','A fresh warrior just starting out',true,10,'warrior_t1'),
  (gen_random_uuid(),'Footman','A seasoned footman with plate armor',false,11,'warrior_t2'),
  (gen_random_uuid(),'Sergeant','A battle-hardened sergeant',false,12,'warrior_t3'),
  (gen_random_uuid(),'Champion','A champion warrior adorned in gold',false,13,'warrior_t4'),
  (gen_random_uuid(),'Warlord','A legendary warlord',false,14,'warrior_t5'),
  -- Mage
  (gen_random_uuid(),'Apprentice','A young mage learning the craft',false,20,'mage_t1'),
  (gen_random_uuid(),'Acolyte','An acolyte with arcane robes',false,21,'mage_t2'),
  (gen_random_uuid(),'Conjurer','A skilled conjurer',false,22,'mage_t3'),
  (gen_random_uuid(),'Sorcerer','A powerful sorcerer',false,23,'mage_t4'),
  (gen_random_uuid(),'Archmage','The Archmage supreme',false,24,'mage_t5'),
  -- Ranger
  (gen_random_uuid(),'Scout','A quick-footed scout',false,30,'ranger_t1'),
  (gen_random_uuid(),'Hunter','A skilled hunter',false,31,'ranger_t2'),
  (gen_random_uuid(),'Tracker','A masterful tracker',false,32,'ranger_t3'),
  (gen_random_uuid(),'Pathfinder','An elite pathfinder',false,33,'ranger_t4'),
  (gen_random_uuid(),'Wildwarden','The legendary Wildwarden',false,34,'ranger_t5'),
  -- Cleric
  (gen_random_uuid(),'Initiate','A devout initiate',false,40,'cleric_t1'),
  (gen_random_uuid(),'Devotee','A faithful devotee',false,41,'cleric_t2'),
  (gen_random_uuid(),'Priestess','A holy priestess',false,42,'cleric_t3'),
  (gen_random_uuid(),'Oracle','A divine oracle',false,43,'cleric_t4'),
  (gen_random_uuid(),'Saint','A blessed saint',false,44,'cleric_t5'),
  -- Rogue
  (gen_random_uuid(),'Pickpocket','A nimble pickpocket',false,50,'rogue_t1'),
  (gen_random_uuid(),'Footpad','A stealthy footpad',false,51,'rogue_t2'),
  (gen_random_uuid(),'Cutpurse','A skilled cutpurse',false,52,'rogue_t3'),
  (gen_random_uuid(),'Shadowblade','A deadly shadowblade',false,53,'rogue_t4'),
  (gen_random_uuid(),'Phantom','The legendary Phantom',false,54,'rogue_t5'),
  -- Bard
  (gen_random_uuid(),'Busker','A cheerful street busker',false,60,'bard_t1'),
  (gen_random_uuid(),'Minstrel','A talented minstrel',false,61,'bard_t2'),
  (gen_random_uuid(),'Troubadour','A renowned troubadour',false,62,'bard_t3'),
  (gen_random_uuid(),'Maestro','A masterful maestro',false,63,'bard_t4'),
  (gen_random_uuid(),'Songweaver','The legendary Songweaver',false,64,'bard_t5');

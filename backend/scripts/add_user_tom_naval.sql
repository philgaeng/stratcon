-- Add user Tom Naval to database
-- Email: tomas.naval@aboitizpower.com
-- Company: Aboitiz Power
-- Entity ID: 2
-- Role: super_admin

-- Insert user (or update if exists)
INSERT OR REPLACE INTO users (
    email, first_name, last_name, company, 
    user_group, entity_id, active, receive_reports_email
)
VALUES (
    'tomas.naval@aboitizpower.com',
    'Tom',
    'Naval',
    'Aboitiz Power',
    'super_admin',
    2,
    1,
    1
);

-- Get the user ID (works for both INSERT and UPDATE)
-- Then create entity assignment
INSERT OR REPLACE INTO entity_user_assignments (
    entity_id, user_id, role
)
SELECT 
    2,
    id,
    'super_admin'
FROM users
WHERE email = 'tomas.naval@aboitizpower.com'
AND NOT EXISTS (
    SELECT 1 FROM entity_user_assignments 
    WHERE user_id = users.id AND entity_id = 2
);


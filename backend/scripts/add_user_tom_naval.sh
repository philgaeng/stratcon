#!/bin/bash
# Add user Tom Naval to database on AWS
# Usage: ./backend/scripts/add_user_tom_naval.sh

DB_PATH="${DATABASE_PATH:-/var/lib/stratcon/data/settings.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at: $DB_PATH"
    exit 1
fi

echo "👤 Adding user Tom Naval to database..."
echo "   Database: $DB_PATH"
echo ""

sqlite3 "$DB_PATH" << 'EOF'
-- Insert or update user
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

-- Create entity assignment
INSERT OR IGNORE INTO entity_user_assignments (
    entity_id, user_id, role
)
SELECT 
    2,
    id,
    'super_admin'
FROM users
WHERE email = 'tomas.naval@aboitizpower.com';

-- Verify
SELECT 
    u.id,
    u.email,
    u.first_name || ' ' || u.last_name as name,
    u.company,
    u.user_group,
    u.entity_id,
    eua.role as assignment_role
FROM users u
LEFT JOIN entity_user_assignments eua ON u.id = eua.user_id AND eua.entity_id = 2
WHERE u.email = 'tomas.naval@aboitizpower.com';
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ User added successfully!"
else
    echo ""
    echo "❌ Error adding user"
    exit 1
fi



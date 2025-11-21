#!/bin/bash
# Update user 6 email to philgaeng@pm.me
# Create new super_admin user with philgaeng@stratcon.ph
# Usage: sudo bash backend/scripts/update_user6_and_create_philippe.sh

DB_PATH="${DATABASE_PATH:-/var/lib/stratcon/data/settings.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at: $DB_PATH"
    exit 1
fi

echo "👤 Updating user 6 and creating new user..."
echo "   Database: $DB_PATH"
echo ""

sqlite3 "$DB_PATH" << 'EOF'
-- Get user 6's current data
SELECT 
    id, email, first_name, last_name, company, position,
    mobile_phone, landline, user_group, entity_id, active, receive_reports_email
FROM users WHERE id = 6;
EOF

echo ""
echo "📝 Updating user 6 email to philgaeng@pm.me..."

sqlite3 "$DB_PATH" << 'EOF'
-- Update user 6 email
UPDATE users 
SET email = 'philgaeng@pm.me'
WHERE id = 6;

-- Create new user with philgaeng@stratcon.ph (copying user 6's data)
INSERT INTO users (
    email, first_name, last_name, company, position,
    mobile_phone, landline, user_group, entity_id, 
    active, receive_reports_email
)
SELECT 
    'philgaeng@stratcon.ph',
    first_name,
    last_name,
    company,
    position,
    mobile_phone,
    landline,
    user_group,
    entity_id,
    active,
    receive_reports_email
FROM users
WHERE id = 6;

-- Get the new user ID
SELECT id as new_user_id FROM users WHERE email = 'philgaeng@stratcon.ph';
EOF

NEW_USER_ID=$(sqlite3 "$DB_PATH" "SELECT id FROM users WHERE email = 'philgaeng@stratcon.ph';")

echo ""
echo "🔗 Creating entity assignment for new user..."

sqlite3 "$DB_PATH" << EOF
-- Create entity assignment for new user (same as user 6)
INSERT INTO entity_user_assignments (
    entity_id, user_id, role
)
SELECT 
    entity_id,
    $NEW_USER_ID,
    'super_admin'
FROM entity_user_assignments
WHERE user_id = 6
LIMIT 1;
EOF

echo ""
echo "✅ Verification:"
echo ""

sqlite3 "$DB_PATH" << 'EOF'
-- Show both users
SELECT 
    u.id,
    u.email,
    u.first_name || ' ' || u.last_name as name,
    u.company,
    u.user_group,
    u.entity_id,
    u.active,
    eua.role as assignment_role
FROM users u
LEFT JOIN entity_user_assignments eua ON u.id = eua.user_id
WHERE u.email IN ('philgaeng@pm.me', 'philgaeng@stratcon.ph')
ORDER BY u.id;
EOF

echo ""
echo "✅ Update complete!"


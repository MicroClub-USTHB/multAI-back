-- name: CreateAdmin :one
INSERT INTO staff_users (email, discord_id, role)
VALUES ($1, $2, 'admin')
RETURNING *;

-- name: CreateMulti :one
INSERT INTO staff_users (email, discord_id, role)
VALUES ($1, $2, 'multi')
RETURNING *;

-- name: GetStaffUserByID :one
SELECT *
FROM staff_users
WHERE id = $1;

-- name: GetStaffUserByEmail :one
SELECT *
FROM staff_users
WHERE email = $1;

-- name: GetAllStaffUsers :many
SELECT *
FROM staff_users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;
-- name: CreateUser :one
INSERT INTO users (email, hashed_password)
VALUES ($1, $2)
RETURNING
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked;

-- name: GetUserByID :one
SELECT
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked
FROM users
WHERE id = $1;

-- name: GetUserByEmail :one
SELECT
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked
FROM users
WHERE email = $1;

-- name: UpdateUserPassword :one
UPDATE users
SET hashed_password = $1,
    updated_at = NOW()
WHERE id = $2
RETURNING
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked;

-- name: UpdateUser :one
UPDATE users
SET email = COALESCE($1, email),
    display_name = COALESCE($2, display_name),
    blocked = COALESCE($3, blocked),
    updated_at = NOW()
WHERE id = $4
RETURNING
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked;

-- name: SetUserBlocked :one
UPDATE users
SET blocked = $1,
    updated_at = NOW()
WHERE id = $2
RETURNING
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked;

-- name: DeleteUser :exec
DELETE FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked
FROM users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- name: SetUserEmbedding :one
UPDATE users
SET face_embedding = $1::vector,
    updated_at = NOW()
WHERE id = $2
RETURNING
    id,
    email,
    hashed_password,
    created_at,
    updated_at,
    display_name,
    face_embedding,
    deleted_at,
    blocked;

-- name: FindClosestUserByEmbedding :one
SELECT id,
       (face_embedding <=> $1::vector) AS distance
FROM users
WHERE face_embedding IS NOT NULL
ORDER BY distance ASC
LIMIT 1;

-- name: CreateUploadRequest :one
INSERT INTO upload_requests (
    event_id,
    drive_file_id,
    requested_by,
    photo_count
) VALUES (
    $1, $2, $3, $4
)
RETURNING
    id,
    event_id,
    drive_file_id,
    requested_by,
    approved_by,
    status,
    created_at,
    approved_at,
    photo_count,
    rejection_reason;

-- name: GetUploadRequestByID :one
SELECT
    id,
    event_id,
    drive_file_id,
    requested_by,
    approved_by,
    status,
    created_at,
    approved_at,
    photo_count,
    rejection_reason
FROM upload_requests
WHERE id = $1;

-- name: ListUploadRequests :many
SELECT
    id,
    event_id,
    drive_file_id,
    requested_by,
    approved_by,
    status,
    created_at,
    approved_at,
    photo_count,
    rejection_reason
FROM upload_requests
WHERE requested_by = $1::uuid
  AND status  = COALESCE(sqlc.narg('p2')::upload_request_status, status)
ORDER BY created_at DESC;

-- name: ApproveUploadRequest :one
UPDATE upload_requests
SET status = 'approved',
    approved_by = $2,
    approved_at = NOW(),
    rejection_reason = NULL
WHERE id = $1
  AND status = 'pending'
RETURNING
    id,
    event_id,
    drive_file_id,
    requested_by,
    approved_by,
    status,
    created_at,
    approved_at,
    photo_count,
    rejection_reason;

-- name: RejectUploadRequest :one
UPDATE upload_requests
SET status = 'rejected',
    approved_by = $2,
    approved_at = NOW(),
    rejection_reason = $3
WHERE id = $1
  AND status = 'pending'
RETURNING
    id,
    event_id,
    drive_file_id,
    requested_by,
    approved_by,
    status,
    created_at,
    approved_at,
    photo_count,
    rejection_reason;

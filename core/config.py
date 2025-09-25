MONGO_URI="mongodb://localhost:27017/bitgpt"
SECRET_KEY="e4c9f1d2a7b64dcb8d2d6d3e9c5d4a6b9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a"

# Matrix placement configuration
# Maximum upline escalation depth for sweepover eligibility checks
MATRIX_MAX_ESCALATION_DEPTH = 60

# Optional Mother ID fallback for Matrix placement when no eligible upline within depth
# Set this to a valid user ObjectId string to enable explicit fallback; leave empty to fallback to topmost eligible only
MATRIX_MOTHER_ID = "68bee3aec1eac053757f5cf1"
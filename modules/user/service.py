from typing import Optional, Dict
import re
from modules.user.model import *
import logging
from math import radians, cos, sin, sqrt, atan2
from bson.son import SON


from mongoengine.queryset.visitor import Q as MQ
from pymongo import ASCENDING, DESCENDING
from bson.regex import Regex

logger = logging.getLogger(__name__)


# Helper: Haversine formula to calculate distance between two coordinates
def calculate_distance(lat1, lng1, lat2, lng2):
    R = 6378137  # Earth radius in meters
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Helper: serialize MongoDB document to JSON-compatible dict
def serialize_doc(doc):
    def convert_value(value):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [convert_value(i) for i in value]
        if isinstance(value, dict):
            return {k: convert_value(v) for k, v in value.items()}
        return value

    return {k: convert_value(v) for k, v in doc.items()}


def fetch_users(
    search_term: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    filters: Optional[Dict] = None,
):
    try:
        pipeline = []
        location_data = filters.get("location") if filters else None
        match_conditions = {}

        if filters:
            if filters.get("tutor_type") and "all" not in filters["tutor_type"]:
                match_conditions["tutor_type"] = {"$in": filters["tutor_type"]}

            if filters.get("class_type") and "all" not in filters["class_type"]:
                match_conditions["class_type"] = {"$in": filters["class_type"]}

            if filters.get("subject_type") and "all" not in filters["subject_type"]:
                match_conditions["subject_type"] = {"$in": filters["subject_type"]}

            if filters.get("versity_type") and "all" not in filters["versity_type"]:
                match_conditions["versity_type"] = {"$in": filters["versity_type"]}

            if filters.get("gender"):
                match_conditions["gender"] = filters["gender"]

            if filters.get("role"):
                match_conditions["role"] = filters["role"]

            if filters.get("is_active") is not None:
                match_conditions["is_active"] = filters["is_active"]

            if filters.get("price_min") is not None:
                match_conditions["price"] = {"$gte": filters["price_min"]}

            if filters.get("price_max") is not None:
                match_conditions.setdefault("price", {})["$lte"] = filters["price_max"]

        # Handle geoNear first if location filtering is needed
        if location_data and location_data.get("latitude") is not None and location_data.get("longitude") is not None:
            lng = float(location_data["longitude"])
            lat = float(location_data["latitude"])
            max_dist_m = float(location_data.get("max_distance_km", 5.0)) * 1000

            pipeline.append({
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [lng, lat]},
                    "distanceField": "distance",
                    "maxDistance": max_dist_m,
                    "spherical": True,
                    "query": match_conditions
                }
            })
        else:
            # Add object ID conversions for class_type and subject_type
            pipeline.append({
                "$addFields": {
                    "class_type_obj": {
                        "$map": {
                            "input": "$class_type",
                            "as": "ct",
                            "in": {"$toObjectId": "$$ct"}
                        }
                    },
                    "subject_type_obj": {
                        "$map": {
                            "input": "$subject_type",
                            "as": "st",
                            "in": {"$toObjectId": "$$st"}
                        }
                    }
                }
            })

            # Match base filters after adding the object ID fields
            if match_conditions:
                pipeline.append({"$match": match_conditions})

            # Add lookups
            pipeline.extend([
                {
                    "$lookup": {
                        "from": "class_type",
                        "localField": "class_type_obj",
                        "foreignField": "_id",
                        "as": "class_type_details"
                    }
                },
                {
                    "$lookup": {
                        "from": "subject_type",
                        "localField": "subject_type_obj",
                        "foreignField": "_id",
                        "as": "subject_type_details"
                    }
                }
            ])

        # Handle search term if not using geoNear
        if search_term and not (location_data and location_data.get("latitude") is not None and location_data.get("longitude") is not None):
            pattern = re.compile(f".*{re.escape(search_term.strip())}.*", re.IGNORECASE)
            search_conditions = {
                "$or": [
                    {"username": {"$regex": pattern.pattern, "$options": "i"}},
                    {"name": {"$regex": pattern.pattern, "$options": "i"}},
                    {"class_type_details": {"$elemMatch": {"name": {"$regex": pattern.pattern, "$options": "i"}}}},
                    {"subject_type_details": {"$elemMatch": {"name": {"$regex": pattern.pattern, "$options": "i"}}}}
                ]
            }
            pipeline.append({"$match": search_conditions})

        # For geoNear queries, we need to add the lookups after geoNear
        if location_data and location_data.get("latitude") is not None and location_data.get("longitude") is not None:
            pipeline.append({
                "$addFields": {
                    "class_type_obj": {
                        "$map": {
                            "input": "$class_type",
                            "as": "ct",
                            "in": {"$toObjectId": "$$ct"}
                        }
                    },
                    "subject_type_obj": {
                        "$map": {
                            "input": "$subject_type",
                            "as": "st",
                            "in": {"$toObjectId": "$$st"}
                        }
                    }
                }
            })
            
            pipeline.extend([
                {
                    "$lookup": {
                        "from": "class_type",
                        "localField": "class_type_obj",
                        "foreignField": "_id",
                        "as": "class_type_details"
                    }
                },
                {
                    "$lookup": {
                        "from": "subject_type",
                        "localField": "subject_type_obj",
                        "foreignField": "_id",
                        "as": "subject_type_details"
                    }
                }
            ])

        sort_direction = -1 if sort_order.lower() == "desc" else 1
        pipeline.append({"$sort": SON([(sort_by, sort_direction)])})
        pipeline.extend([
            {"$skip": (page - 1) * limit},
            {"$limit": limit}
        ])

        logger.debug(f"Aggregation pipeline: {pipeline}")

        collection = UserDocument._get_collection()
        users_cursor = collection.aggregate(pipeline)
        
        # EXCLUDE hashed_password and otp from each user document
        users = [
            {k: v for k, v in serialize_doc(doc).items() if k not in {"hashed_password", "otp"}}
            for doc in users_cursor
        ]

        count_pipeline = pipeline[:-2]  # remove skip and limit stages
        count_pipeline.append({"$count": "total"})
        total_cursor = collection.aggregate(count_pipeline)
        total_result = list(total_cursor)
        total = total_result[0]["total"] if total_result else 0

        logger.debug(f"Aggregation returned documents: {users}")
        logger.debug(f"Total count from aggregation: {total}")

        return {
            "meta": {"page": page, "limit": limit, "total": total},
            "data": users
        }

    except Exception as e:
        logger.error(f"[FETCH_USERS] Error: {str(e)}", exc_info=True)
        raise ValueError("Error fetching users")




    # page=1&limit=12&sort_by=created_at&sort_order=desc&price_min=500&price_max=5000&is_active=true&latitude=22.816042&longitude=89.56425&tutor_type=68381c2ddc7b2c2530ac75aa&class_type=68381fa9dc7b2c2530ac75c2&subject_type=68381ff5dc7b2c2530ac75c9
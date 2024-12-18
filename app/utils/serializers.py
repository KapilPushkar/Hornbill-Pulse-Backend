from bson import ObjectId

def serialize_to_response(data: dict) -> dict:
    if "_id" in data:
        data["_id"] = str(data["_id"])
    return data 
def coordinate_serializer(coordinate) -> dict:
    return {
        "_id": str(coordinate["_id"]),
        "coordinates": coordinate["coordinates"]
    }

def coordinates_serializer(coordinates) -> list:
    result = []
    for doc in coordinates:
        if "coordinates" in doc:
            result.extend(doc["coordinates"])
    return result 
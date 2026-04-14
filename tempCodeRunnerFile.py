t()

        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return "User already exists"

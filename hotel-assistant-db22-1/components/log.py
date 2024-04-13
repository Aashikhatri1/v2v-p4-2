# def print_and_save(message, file_path='output.txt'):
#     # print(message)
#     with open(file_path, 'a') as file:  # 'a' mode for appending to the file
#         file.write(message)

# # Example usage
# # print_and_save("Hello, World!")


from pymongo import MongoClient



# def print_and_save(message, file_path='output.txt'):
#     client = MongoClient('mongodb+srv://aiappuser:vYdXfgvsnPL51ExB@cluster0.54uxknw.mongodb.net/')

#     # Select the database
#     db = client['V2VBot']

#     # Select the collection
#     collection = db['logs']

#     # Document to be inserted
#     time_stamp = {"time_stamp": file_path}

#     # The new values to be updated or inserted
#     new_values = {"$set": {"message": message}}

#     # Perform the update operation with upsert=True
#     result = collection.update_one(time_stamp, new_values, upsert=True)

#     # Output based on the operation performed
# #     if result.upserted_id:
# #         print(f"Document inserted with ID: {result.upserted_id}")
# #     else:
# #         print("Document updated")

# # print_and_save('Hello', file_path='12345')

client = MongoClient('mongodb+srv://aiappuser:vYdXfgvsnPL51ExB@cluster0.54uxknw.mongodb.net/')

    # Select the database
db = client['V2VBot']

# Select the collection
collection = db['logs']

async def print_and_save(message, file_path='output.txt'):
    

    # Query to find if the document exists
    document = collection.find_one({"time_stamp": file_path})

    # Determine the next message field name
    if document:
        # Find the maximum message index already in use
        message_fields = [field for field in document.keys() if field.startswith("message")]
        if message_fields:
            last_message_index = max([int(field.replace("message", "")) for field in message_fields])
        else:
            last_message_index = 0
        next_message_field = f"message{last_message_index + 1}"
        update_result = collection.update_one({"time_stamp": file_path}, {"$set": {next_message_field: message}})
        # print("Document updated")
    else:
        # If the document does not exist, create a new one with message1
        new_document = {
            "time_stamp": file_path,
            "message1": message
        }
        insert_result = collection.insert_one(new_document)
        # print(f"Document inserted with ID: {insert_result.inserted_id}")

# print_and_save('Hello2', file_path='123456')
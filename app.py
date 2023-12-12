import motor.motor_asyncio
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import time
import random
import uuid

app = FastAPI()
today = date.today()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uri = "mongodb+srv://Capstone:uxlewge2DC1PncFp@cluster0.09qreau.mongodb.net/?retryWrites=true&w=majority"

# Create a new client and connect to the server
client = motor.motor_asyncio.AsyncIOMotorClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You have successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client["bank_db"]

card_details_collection = db["card_details"]
account_details_collection = db["account_details"]
transactions_collection = db["transactions"]
users_collection = db["users_collection"]
profile_collection = db["user_profiles"]


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    contact: int
    address: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CardDetails(BaseModel):
    name: str
    account_number: int
    expiry: str
    cvv: int
    validity: str

class AccountDetails(BaseModel):
    account_type: str
    account_number: int
    account_balance: int
    account_status: str
    interest_rate: float
    transaction_limits: int
    account_opening_date: str
    email: str

class TransactionDetails(BaseModel):
    time: int
    amount: int
    transaction_type: str    # credit / debit
    transaction_status: str
    transaction_id: int
    reference_number: int
    account_number: int
    current_balance: int


class ProfileInfo(BaseModel):
    name: str
    contact: int
    address: str
    email: EmailStr

class Funds(BaseModel):
    sender: int
    receiver: int
    amount: int

@app.post("/signup")
def signup(user: SignupRequest):
    user_dict = user.dict()
    # user_account_details = user.dict()
    user_dict["password"] = user.password 
    users_collection.insert_one(user_dict)
    # account_type: str
    # account_number: int
    # account_balance: int
    # account_status: str
    # interest_rate: float
    # transaction_limits: int
    # account_opening_date: str
    # mail: str
    user_account_details= {}
    user_account_details["account_type"] = "saving"
    user_account_details["account_number"] = random.randint(100000, 999999)
    user_account_details["account_balance"] = 50000
    user_account_details["account_status"] = "active"
    user_account_details["interest_rate"] = 6
    user_account_details["transaction_limits"] = 25
    user_account_details["account_opening_date"] = today.strftime("%m/%d/%Y")
    user_account_details["email"] = user.email
    # json_object = json.dumps(user_account_details, indent = 4) 
    create_account_details(user_account_details)
    return {"message": "Signup successful"}


@app.post("/signup")
def signup(user: SignupRequest):
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_dict = user.dict()
    user_dict["password"] = user.password 
    users_collection.insert_one(user_dict)
    return {"message": "Signup successful"}

@app.post("/login")
async def login(user: LoginRequest):
    stored_user = await users_collection.find_one({"email": user.email, "password": user.password})
    print("hello avneesh bhayia")
    print(stored_user)
    if stored_user:
        return {"message": "Login successful"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dashboard Endpoints
@app.get("/dashboard/card-details/{account_number}")
async def get_card_details(account_number: int):
    result = await card_details_collection.find_one({}, {"_id": 0})
    result = await card_details_collection.find_one({"account_number": account_number}, {"_id": 0})
    print(result)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Card details not found")

@app.post("/dashboard/card-details")
def create_card_details(card_details: CardDetails):
    card_details_collection.replace_one({}, card_details.dict(), upsert=True)
    return card_details.dict()

@app.get("/dashboard/account-details/{email}")
async def get_account_details(email: str):
    result = await account_details_collection.find_one({"email": email}, {"_id": 0})
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Account details not found")

# @app.post("/dashboard/account-details")
def create_account_details(account_details: AccountDetails):
    # account_detail = account_details.dict()
    # user_dict["password"] = user.password 
    account_details_collection.insert_one(account_details)
    print ("hello")
    # account_details_collection.replace_one({}, account_details.dict(), upsert=True)
    return {"status": "success"}

@app.put("/dashboard/account-details")
def update_account_details(account_details: AccountDetails):
    account_details_collection.replace_one({}, account_details.dict(), upsert=True)
    return account_details.dict()

# Transaction Endpoints
@app.get("/transactions/{account_number}")
async def get_transactions(account_number: int):
    result = transactions_collection.find({"account_number": account_number}, {"_id": 0}).sort({"time" : -1})
    result_list = await result.to_list(length=100)
    print(result_list)
    return result_list


# @app.post("/transactions")
def create_transaction(transaction: TransactionDetails):
    transactions_collection.insert_one(transaction)
    

@app.get("/profile/{email}")
async def update_profile(email: str):
    result = await  users_collection.find_one({"email": email}, {"_id": 0})
    print(email)
    print(result)
    if result is not None:
        return result
    else:
        return {"error": "Profile not found"}
    
@app.post("/transfer-funds")
async def transfer_funds(funds: Funds):
    # return {"funds": "suraj"}

    sender_account = await account_details_collection.find_one({"account_number": funds.sender})
    receiver_account = await account_details_collection.find_one({"account_number": funds.receiver})

    if not sender_account or not receiver_account:
        raise HTTPException(status_code=404, detail="Sender or receiver not found")
    
    sender_balance = sender_account.get("account_balance", 0)
    print(funds.amount)
    if sender_balance < funds.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    new_sender_balance = sender_balance - funds.amount
    new_receiver_balance = receiver_account.get("account_balance", 0) + funds.amount

    await account_details_collection.update_one({"account_number": funds.sender}, {"$set": {"account_balance": new_sender_balance}})
    await account_details_collection.update_one({"account_number": funds.receiver}, {"$set": {"account_balance": new_receiver_balance}})
    # date: str
    # time: str
    # amount: int
    # transaction_type: str    # credit / debit
    # transaction_status: str
    # transaction_id: int
    # reference_number: int
    # account_number: int
    credit_trans = {}
    credit_trans["time"]=int(time.time())
    credit_trans["amount"] = funds.amount
    credit_trans["transaction_type"] = "credit"
    credit_trans["transaction_status"] = "success"
    credit_trans["transaction_id"] = uuid.uuid4().hex
    credit_trans["reference_number"] = uuid.uuid4().hex
    credit_trans["account_number"] = funds.receiver
    credit_trans["current_balance"] = new_receiver_balance

    debit_trans = {}
    debit_trans["time"] = int((time.time()))
    debit_trans["amount"] = funds.amount
    debit_trans["transaction_type"] = "debit"
    debit_trans["transaction_status"] = "success"
    debit_trans["transaction_id"] = credit_trans["transaction_id"]
    debit_trans["reference_number"] = credit_trans["reference_number"]
    debit_trans["account_number"] = funds.sender
    debit_trans["current_balance"] = new_sender_balance
    create_transaction(credit_trans)
    create_transaction(debit_trans)
    return {"message": "Transaction successful", "transaction_details": funds.dict()}

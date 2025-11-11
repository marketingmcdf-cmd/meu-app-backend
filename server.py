from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'meu_app_db')]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    age: int
    weight: float  # in kg
    height: float  # in cm
    sex: str  # "male" or "female"
    gym_attendance: bool
    goal_weight: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    name: str
    age: int
    weight: float
    height: float
    sex: str
    gym_attendance: bool
    goal_weight: Optional[float] = None

class WaterLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float  # in ml
    date: str  # YYYY-MM-DD
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WaterLogCreate(BaseModel):
    user_id: str
    amount: float

class ProgressLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    weight: float
    date: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProgressLogCreate(BaseModel):
    user_id: str
    weight: float

# User endpoints
@api_router.post("/user", response_model=User)
async def create_user(user_input: UserCreate):
    user_dict = user_input.model_dump()
    user_obj = User(**user_dict)
    
    doc = user_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    return user_obj

@api_router.get("/user/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return user

@api_router.put("/user/{user_id}", response_model=User)
async def update_user(user_id: str, user_input: UserCreate):
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_dict = user_input.model_dump()
    await db.users.update_one({"id": user_id}, {"$set": update_dict})
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0})
    if isinstance(updated['created_at'], str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    
    return updated

# Water tracking endpoints
@api_router.post("/water", response_model=WaterLog)
async def log_water(water_input: WaterLogCreate):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    water_dict = water_input.model_dump()
    water_dict['date'] = today
    water_obj = WaterLog(**water_dict)
    
    doc = water_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.water_logs.insert_one(doc)
    return water_obj

@api_router.get("/water/{user_id}", response_model=List[WaterLog])
async def get_water_logs(user_id: str, date: Optional[str] = None):
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    logs = await db.water_logs.find({"user_id": user_id, "date": date}, {"_id": 0}).to_list(1000)
    
    for log in logs:
        if isinstance(log['timestamp'], str):
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
    
    return logs

@api_router.get("/water/calculate/{user_id}")
async def calculate_water_goal(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Formula: 35ml x body weight (kg)
    water_goal = user['weight'] * 35  # in ml
    
    return {
        "user_id": user_id,
        "daily_goal_ml": water_goal,
        "daily_goal_liters": round(water_goal / 1000, 2)
    }

# Meal suggestions
@api_router.get("/meals")
async def get_meals():
    meals = {
        "breakfast": [
            {
                "name": "Omelete com Vegetais",
                "ingredients": ["2 ovos", "Espinafre", "Tomate", "Cebola", "Pimentão"],
                "calories": 250,
                "prep_time": "10 min"
            },
            {
                "name": "Aveia com Frutas",
                "ingredients": ["50g aveia", "1 banana", "Morangos", "1 colher mel", "Canela"],
                "calories": 300,
                "prep_time": "5 min"
            },
            {
                "name": "Iogurte Natural com Granola",
                "ingredients": ["200g iogurte natural", "30g granola", "Frutas vermelhas", "Chia"],
                "calories": 280,
                "prep_time": "3 min"
            }
        ],
        "lunch": [
            {
                "name": "Frango Grelhado com Legumes",
                "ingredients": ["150g peito de frango", "Brócolis", "Cenoura", "Arroz integral", "Azeite"],
                "calories": 450,
                "prep_time": "25 min"
            },
            {
                "name": "Peixe Assado com Salada",
                "ingredients": ["150g filé de peixe", "Alface", "Tomate", "Pepino", "Batata doce"],
                "calories": 400,
                "prep_time": "30 min"
            },
            {
                "name": "Salada de Quinoa",
                "ingredients": ["100g quinoa", "Grão de bico", "Abacate", "Folhas verdes", "Limão"],
                "calories": 420,
                "prep_time": "20 min"
            }
        ],
        "dinner": [
            {
                "name": "Sopa de Legumes",
                "ingredients": ["Cenoura", "Abobrinha", "Batata", "Cebola", "Alho"],
                "calories": 200,
                "prep_time": "30 min"
            },
            {
                "name": "Omelete Light",
                "ingredients": ["3 claras", "1 gema", "Cogumelos", "Queijo branco", "Tomate"],
                "calories": 220,
                "prep_time": "10 min"
            },
            {
                "name": "Salada Caesar com Frango",
                "ingredients": ["100g frango grelhado", "Alface romana", "Parmesão", "Molho light"],
                "calories": 350,
                "prep_time": "15 min"
            }
        ],
        "snack": [
            {
                "name": "Mix de Castanhas",
                "ingredients": ["Amêndoas", "Castanha de caju", "Nozes"],
                "calories": 150,
                "prep_time": "0 min"
            },
            {
                "name": "Frutas com Pasta de Amendoim",
                "ingredients": ["1 maçã", "1 colher pasta amendoim"],
                "calories": 180,
                "prep_time": "2 min"
            },
            {
                "name": "Smoothie Verde",
                "ingredients": ["Espinafre", "Banana", "Abacaxi", "Água de coco"],
                "calories": 160,
                "prep_time": "5 min"
            }
        ]
    }
    
    return meals

# Workout suggestions
@api_router.get("/workouts/{user_id}")
async def get_workouts(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user['gym_attendance']:
        workouts = {
            "type": "Academia",
            "routine": [
                {
                    "day": "Segunda-feira",
                    "focus": "Peito e Tríceps",
                    "exercises": [
                        {"name": "Supino Reto", "sets": "4x10", "rest": "60s"},
                        {"name": "Supino Inclinado", "sets": "3x12", "rest": "60s"},
                        {"name": "Crucifixo", "sets": "3x12", "rest": "45s"},
                        {"name": "Tríceps Pulley", "sets": "3x15", "rest": "45s"},
                        {"name": "Tríceps Testa", "sets": "3x12", "rest": "45s"}
                    ]
                },
                {
                    "day": "Quarta-feira",
                    "focus": "Costas e Bíceps",
                    "exercises": [
                        {"name": "Puxada Frontal", "sets": "4x10", "rest": "60s"},
                        {"name": "Remada Curvada", "sets": "3x12", "rest": "60s"},
                        {"name": "Pullover", "sets": "3x12", "rest": "45s"},
                        {"name": "Rosca Direta", "sets": "3x12", "rest": "45s"},
                        {"name": "Rosca Martelo", "sets": "3x12", "rest": "45s"}
                    ]
                },
                {
                    "day": "Sexta-feira",
                    "focus": "Pernas e Ombros",
                    "exercises": [
                        {"name": "Agachamento", "sets": "4x12", "rest": "90s"},
                        {"name": "Leg Press", "sets": "3x15", "rest": "60s"},
                        {"name": "Cadeira Extensora", "sets": "3x12", "rest": "45s"},
                        {"name": "Desenvolvimento", "sets": "4x10", "rest": "60s"},
                        {"name": "Elevação Lateral", "sets": "3x15", "rest": "45s"}
                    ]
                }
            ],
            "cardio": "20-30 min após treino ou dias alternados"
        }
    else:
        workouts = {
            "type": "Casa (Funcional)",
            "routine": [
                {
                    "day": "Segunda/Quarta/Sexta",
                    "focus": "Corpo Inteiro",
                    "exercises": [
                        {"name": "Flexões", "sets": "3x12", "rest": "45s"},
                        {"name": "Agachamento Livre", "sets": "4x15", "rest": "45s"},
                        {"name": "Prancha", "sets": "3x45s", "rest": "30s"},
                        {"name": "Afundo", "sets": "3x12 cada perna", "rest": "45s"},
                        {"name": "Burpees", "sets": "3x10", "rest": "60s"},
                        {"name": "Mountain Climbers", "sets": "3x20", "rest": "45s"}
                    ]
                },
                {
                    "day": "Terça/Quinta",
                    "focus": "Cardio + Core",
                    "exercises": [
                        {"name": "Polichinelos", "sets": "3x30", "rest": "30s"},
                        {"name": "Abdominal", "sets": "3x20", "rest": "30s"},
                        {"name": "Abdominal Bicicleta", "sets": "3x20", "rest": "30s"},
                        {"name": "Prancha Lateral", "sets": "3x30s cada lado", "rest": "30s"},
                        {"name": "High Knees", "sets": "3x30s", "rest": "30s"}
                    ]
                }
            ],
            "notes": "Sempre aqueça por 5 minutos antes de começar"
        }
    
    return workouts

# Progress tracking
@api_router.post("/progress", response_model=ProgressLog)
async def log_progress(progress_input: ProgressLogCreate):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    progress_dict = progress_input.model_dump()
    progress_dict['date'] = today
    progress_obj = ProgressLog(**progress_dict)
    
    doc = progress_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.progress_logs.insert_one(doc)
    return progress_obj

@api_router.get("/progress/{user_id}", response_model=List[ProgressLog])
async def get_progress(user_id: str):
    logs = await db.progress_logs.find({"user_id": user_id}, {"_id": 0}).sort("date", 1).to_list(1000)
    
    for log in logs:
        if isinstance(log['timestamp'], str):
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
    
    return logs

@api_router.get("/bmi/{user_id}")
async def calculate_bmi(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    height_m = user['height'] / 100
    bmi = user['weight'] / (height_m ** 2)
    
    if bmi < 18.5:
        status = "Baixo peso"
        color = "#3B82F6"
    elif 18.5 <= bmi < 25:
        status = "Peso normal"
        color = "#10B981"
    elif 25 <= bmi < 30:
        status = "Sobrepeso"
        color = "#F59E0B"
    else:
        status = "Obesidade"
        color = "#EF4444"
    
    return {
        "user_id": user_id,
        "bmi": round(bmi, 1),
        "status": status,
        "color": color
    }

# Motivational messages
@api_router.get("/motivation")
async def get_motivation():
    messages = [
        "Você está indo bem! Continue assim!",
        "Não desista hoje! Cada passo conta.",
        "Seu corpo agradece cada escolha saudável.",
        "Acredite em si mesmo. Você consegue!",
        "Pequenos progressos diários levam a grandes resultados.",
        "Você é mais forte do que pensa!",
        "Mantenha o foco no seu objetivo.",
        "Cada dia é uma nova oportunidade.",
        "Sua saúde é seu maior tesouro.",
        "Consistência é a chave do sucesso!"
    ]
    
    return {"message": random.choice(messages)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>🚀 API do Meu App está funcionando!</h1>"

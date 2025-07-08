
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Import Stripe payment endpoints
from server import *

# Import your API routers
from admin_login import router as admin_router
from dishes_api import router as dishes_router
from menu_api import router as menu_router
from order_master import router as order_router
from customer_api import router as customer_router
from promotion_api import router as promotion_router
from cms_api import router as cms_router
from contact_us_api import router as contact_us_router
from gallery_api import router as gallery_router 
from subscriber_api import router as subscriber_router
from aboutus_items import router as aboutus_router
from aboutus_howitworks_api import router as howitworks_router
from aboutus_whychoose_api import router as aboutus_whychoose_router
from tax_api import router as tax_router
from msg_api import router as msg_router

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_router)
app.include_router(dishes_router)
app.include_router(menu_router)
app.include_router(order_router)
app.include_router(customer_router)
app.include_router(promotion_router)
app.include_router(cms_router)
app.include_router(contact_us_router)
app.include_router(gallery_router)
app.include_router(subscriber_router)
app.include_router(aboutus_router)
app.include_router(howitworks_router)
app.include_router(aboutus_whychoose_router)
app.include_router(tax_router)
app.include_router(msg_router)


from fastapi.staticfiles import StaticFiles
import os

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")



@app.get("/")
def root():
    return {"message": "Welcome to Global Tiffin API"}





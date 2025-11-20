"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional

# Example schemas (you can keep or remove if unused):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Portfolio-specific schemas

class Video(BaseModel):
    """Video metadata for uploaded videos. Collection: "video""" 
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Short description")
    filename: str = Field(..., description="Stored file name on server")
    url: str = Field(..., description="Public URL to stream the video")
    mime_type: Optional[str] = Field(None, description="MIME type of the uploaded file")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")

class ContactMessage(BaseModel):
    """Contact messages sent from the site. Collection: "contactmessage"""
    name: str = Field(..., description="Sender name")
    email: EmailStr = Field(..., description="Sender email")
    message: str = Field(..., min_length=1, max_length=5000, description="Message body")

import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from openai import AsyncAzureOpenAI
import asyncio

load_dotenv()

Base = declarative_base()

class PatentsList(Base):
    __tablename__ = 'patents_list'

    sys_id = Column(Integer, primary_key=True, autoincrement=True)
    official_title = Column(String(255), nullable=False)
    tech_sector = Column(String(255))
    inventor = Column(String(255))
    department = Column(String(255))
    country_region = Column(String(100))
    google_patent_link = Column(Text)
    ai_summary = Column(Text)
    embedding = Column(Vector(1536))  # Adjust dimensions as needed
    # metadata = Column(JSONB, nullable=False, default=dict)
    created_dt = Column(TIMESTAMP, server_default='CURRENT_TIMESTAMP')
    is_tech = Column(Boolean)
    ai_short_summary = Column(Text)



# Replace the environment variable with the properly formatted connection string
DATABASE_URL = os.getenv("AZURE_POSTGRES_CONNECTION")
engine = create_engine(DATABASE_URL, connect_args={'client_encoding': 'utf8'})

# Initialize OpenAI and Supabase clients
openai_client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_version=os.getenv('AZURE_API_VERSION'),
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
)


Session = sessionmaker(bind=engine)
session = Session()


async def get_embedding(text: str) -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error


async def update_embedding():
    # Fetch records where ai_summary is NOT NULL but embedding IS NULL or is a zero vector
    records = session.query(PatentsList).filter(
        PatentsList.ai_summary.isnot(None),
        (PatentsList.embedding.is_(None) | (PatentsList.embedding == ([0] * 1536)))
    ).all()

    for record in records:
        # Generate the summary (replace this with your actual summary generation logic)
        # summary = generate_summary(record)

        embedding = await get_embedding(record.ai_summary)

        # Update the ai_summary field
        stmt = (
            update(PatentsList).
            where(PatentsList.sys_id == record.sys_id).
            values(embedding=embedding)
        )
        session.execute(stmt)

    # Commit the changes to the database
    session.commit()


async def main():
    # Get URLs from Pydantic AI docs
    await update_embedding()


if __name__ == "__main__":
    asyncio.run(main())
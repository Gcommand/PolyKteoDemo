import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.ext.declarative import declarative_base

# Load environment variables
load_dotenv()

# Get database URL and validate
DATABASE_URL = os.getenv("AZURE_POSTGRES_CONNECTION")
if not DATABASE_URL:
    raise ValueError("AZURE_POSTGRES_CONNECTION environment variable is not set")

Base = declarative_base()


class OldPatentsList(Base):  # Temporary model to read the old column
    __tablename__ = 'patents_list'
    sys_id = Column(Integer, primary_key=True)  # Changed from String to Integer
    tech_sector = Column(String)  # The old column we are reading from
    __table_args__ = {'extend_existing': True}


class TechSectors(Base):
    __tablename__ = 'tech_sectors'
    tech_sector_id = Column(Integer, primary_key=True, autoincrement=True)
    tech_sector_name = Column(String, unique=True, nullable=False)
    __table_args__ = {'extend_existing': True}


class PatentTechSectors(Base):
    __tablename__ = 'patent_tech_sectors'
    patent_sys_id = Column(Integer, ForeignKey('patents_list.sys_id'), primary_key=True)
    tech_sector_id = Column(Integer, ForeignKey('tech_sectors.tech_sector_id'), primary_key=True)
    __table_args__ = {'extend_existing': True}


# Create engine with proper connection arguments
engine = create_engine(DATABASE_URL, connect_args={'client_encoding': 'utf8'})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_tech_sectors():
    db = SessionLocal()
    try:
        # First, clean the tech_sector data by removing newlines
        # print("Cleaning tech_sector data...")
        # db.execute("""
        #            UPDATE patents_list
        #            SET tech_sector = REPLACE(REPLACE(tech_sector, E '\r', ''), E '\n', '')
        #            WHERE tech_sector IS NOT NULL
        #            """)
        # db.commit()
        # print("Data cleaning completed.")

        # Get all patents with tech_sector data
        print("Fetching patents with tech_sector data...")
        all_patents = db.query(OldPatentsList).filter(OldPatentsList.tech_sector.isnot(None)).all()
        print(f"Found {len(all_patents)} patents with tech_sector data.")

        # Get existing tech sectors
        print("Fetching existing tech sectors...")
        tech_sector_map = {ts.tech_sector_name: ts.tech_sector_id for ts in db.query(TechSectors).all()}
        print(f"Found {len(tech_sector_map)} existing tech sectors.")

        new_links = []
        skipped_sectors = set()

        print("Creating patent-tech sector relationships...")
        for patent in all_patents:
            if not patent.tech_sector:
                continue

            # Split by '/' and trim whitespace
            sector_names_from_patent = [s.strip() for s in patent.tech_sector.split('/') if s.strip()]

            for name in sector_names_from_patent:
                if name in tech_sector_map:
                    # Check if link already exists
                    exists = db.query(PatentTechSectors).filter_by(
                        patent_sys_id=patent.sys_id,
                        tech_sector_id=tech_sector_map[name]
                    ).first()
                    if not exists:
                        new_links.append(PatentTechSectors(
                            patent_sys_id=patent.sys_id,
                            tech_sector_id=tech_sector_map[name]
                        ))
                else:
                    skipped_sectors.add(name)

        if new_links:
            print(f"Adding {len(new_links)} new relationships...")
            db.add_all(new_links)
            db.commit()
            print(f"Successfully created {len(new_links)} links in patent_tech_sectors.")

        if skipped_sectors:
            print("\nWarning: The following tech sectors were not found in the tech_sectors table:")
            for sector in sorted(skipped_sectors):
                print(f"  - {sector}")

    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("Starting tech sector migration...")
    migrate_tech_sectors()
    print("Migration finished.")
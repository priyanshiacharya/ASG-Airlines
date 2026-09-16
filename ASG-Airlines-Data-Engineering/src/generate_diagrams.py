"""
ASG Airlines Data Engineering Pipeline
Step 12: Architecture & Data Flow Diagram Generator

Generates high-resolution PNG diagrams:
  - docs/architecture_diagram.png
  - docs/data_flow_diagram.png
"""

import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure docs directory exists
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)


def create_architecture_diagram():
    """Generates 5-layer System Architecture Diagram."""
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    fig.patch.set_facecolor('#0f172a') # Sleek dark background
    ax.set_facecolor('#0f172a')

    # Title
    ax.text(0.5, 0.95, "ASG AIRLINES DATA ENGINEERING - SYSTEM ARCHITECTURE",
            color='#f8fafc', fontsize=16, fontweight='bold', ha='center', va='center')
    ax.text(0.5, 0.92, "Local Python / Pandas / Power BI Data Pipeline",
            color='#94a3b8', fontsize=11, ha='center', va='center')

    layers = [
        {"title": "1. RAW DATA LAYER", "color": "#1e293b", "border": "#3b82f6", "y": 0.77, "h": 0.11,
         "items": ["UseCase - Airlines.xlsx (data/raw/)", "4 Sheets: flights, payments, bookings, passengers"]},
        
        {"title": "2. PROCESSING & PIPELINE LAYER (Python 3.14 + Pandas)", "color": "#1e293b", "border": "#8b5cf6", "y": 0.60, "h": 0.13,
         "items": ["Ingestion (ingestion.py)  |  Quality Checks (data_quality.py)  |  Cleaning (data_cleaning.py)",
                   "Transformation (data_transformation.py)  |  Flight Duration & Overnight (flight_duration.py)",
                   "Data Validation (data_validation.py)  |  Final Synthesis (final_dataset.py)  |  KPI Model (kpi_model.py)"]},
        
        {"title": "3. LOCAL STORAGE LAYER", "color": "#1e293b", "border": "#06b6d4", "y": 0.44, "h": 0.12,
         "items": ["data/raw/ (Raw excel immutable backup)", "data/processed/ (Cleaned CSVs, KPI summary tables, validation reports)",
                   "logs/ (ingestion.log, data_cleaning.log, data_validation.log, etc.)"]},
        
        {"title": "4. ANALYTICS & DATA MODEL LAYER", "color": "#1e293b", "border": "#10b981", "y": 0.27, "h": 0.13,
         "items": ["Fact Table: FactFlights (1,004 rows) | Star Schema Data Model",
                   "Dimensions: DimAirline, DimRoute, DimTime | Audit Trail: rejected_flights.csv (16 rows)",
                   "KPI Engine: Avg Duration (164.75m), Route Traffic (30 routes), Market Share (4 airlines)"]},
        
        {"title": "5. VISUALIZATION & REPORTING LAYER", "color": "#1e293b", "border": "#f59e0b", "y": 0.10, "h": 0.13,
         "items": ["Microsoft Power BI Desktop", "Interactive ASG Airlines Flight Operations Dashboard",
                   "4 Core Pages: Executive Overview, Route & Traffic, Operational & Duration, Data Quality & Governance"]}
    ]

    for layer in layers:
        rect = patches.FancyBboxPatch((0.05, layer["y"]), 0.90, layer["h"],
                                     boxstyle="round,pad=0.02,rounding_size=0.02",
                                     linewidth=2, edgecolor=layer["border"], facecolor=layer["color"])
        ax.add_patch(rect)
        
        ax.text(0.08, layer["y"] + layer["h"] - 0.03, layer["title"],
                color=layer["border"], fontsize=11, fontweight='bold', va='center')
        
        for i, text in enumerate(layer["items"]):
            ax.text(0.08, layer["y"] + layer["h"] - 0.06 - (i * 0.03), text,
                    color='#e2e8f0', fontsize=9.5, va='center')

    # Draw vertical connecting arrows between layers
    arrows_y = [(0.77, 0.73), (0.60, 0.56), (0.44, 0.40), (0.27, 0.23)]
    for y1, y2 in arrows_y:
        ax.annotate('', xy=(0.5, y2), xytext=(0.5, y1),
                    arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=2, mutation_scale=15))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    out_path = os.path.join(DOCS_DIR, "architecture_diagram.png")
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✓ Architecture diagram saved to: {out_path}")


def create_data_flow_diagram():
    """Generates Linear Data Flow Diagram."""
    fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    ax.text(0.5, 0.97, "ASG AIRLINES END-TO-END DATA FLOW DIAGRAM",
            color='#f8fafc', fontsize=16, fontweight='bold', ha='center', va='center')
    ax.text(0.5, 0.95, "Step-by-Step Data Pipeline Progression",
            color='#94a3b8', fontsize=11, ha='center', va='center')

    steps = [
        {"num": "1", "name": "Raw Excel Dataset", "desc": "UseCase - Airlines.xlsx (data/raw/)", "color": "#3b82f6"},
        {"num": "2", "name": "Python / Pandas Ingestion", "desc": "src/ingestion.py -> Raw Sheet Ingestion & Schema Inspection", "color": "#6366f1"},
        {"num": "3", "name": "Data Quality Checks", "desc": "src/data_quality.py -> Audit Nulls, Duplicates, Malformed Records", "color": "#8b5cf6"},
        {"num": "4", "name": "Data Cleaning", "desc": "src/data_cleaning.py -> Deduplicate (16 removed), Impute Airlines/Amounts, Mask PII", "color": "#ec4899"},
        {"num": "5", "name": "Data Transformation", "desc": "src/data_transformation.py -> Create Routes, Extract Hours, Categorize Shifts", "color": "#14b8a6"},
        {"num": "6", "name": "Flight Duration & Overnight Handling", "desc": "src/flight_duration.py -> Calc Minutes/Hours, Flag 122 Overnight Flights", "color": "#10b981"},
        {"num": "7", "name": "Data Validation", "desc": "src/data_validation.py -> 19 Automated Checks (100% PASS -> READY FOR ANALYTICS)", "color": "#84cc16"},
        {"num": "8", "name": "Final Analytical Dataset & KPI Model", "desc": "final_flights.csv & kpi_summary.csv -> Fact & Dimension Tables Export", "color": "#eab308"},
        {"num": "9", "name": "Power BI Import & DAX Modeling", "desc": "Star Schema Model (FactFlights <-> DimAirline, DimRoute, DimTime)", "color": "#f97316"},
        {"num": "10", "name": "Interactive Flight Operations Dashboard", "desc": "4-Page Executive Dashboard (Overview, Routes, Operations, Quality)", "color": "#ef4444"}
    ]

    total_steps = len(steps)
    y_start = 0.89
    spacing = 0.082

    for idx, step in enumerate(steps):
        y = y_start - (idx * spacing)
        
        # Step box
        rect = patches.FancyBboxPatch((0.10, y), 0.80, 0.06,
                                     boxstyle="round,pad=0.015,rounding_size=0.015",
                                     linewidth=2, edgecolor=step["color"], facecolor="#1e293b")
        ax.add_patch(rect)
        
        # Step Number Badge
        circle = patches.Circle((0.15, y + 0.03), 0.022, facecolor=step["color"], edgecolor="none")
        ax.add_patch(circle)
        ax.text(0.15, y + 0.03, step["num"], color="#ffffff", fontsize=10, fontweight='bold', ha='center', va='center')
        
        # Step Name & Description
        ax.text(0.20, y + 0.04, step["name"], color="#f8fafc", fontsize=11, fontweight='bold', va='center')
        ax.text(0.20, y + 0.018, step["desc"], color="#94a3b8", fontsize=9, va='center')
        
        # Arrow down
        if idx < total_steps - 1:
            ax.annotate('', xy=(0.5, y - 0.02), xytext=(0.5, y),
                        arrowprops=dict(arrowstyle="->", color=step["color"], lw=2, mutation_scale=12))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    out_path = os.path.join(DOCS_DIR, "data_flow_diagram.png")
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✓ Data flow diagram saved to: {out_path}")


def main():
    create_architecture_diagram()
    create_data_flow_diagram()


if __name__ == "__main__":
    main()

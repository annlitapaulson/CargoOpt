from fastapi import FastAPI
from container import Container
from ship import Ship, Bay
from genetic_optimizer import GeneticOptimizer
from rl_optimizer import RLOptimizer
import time
import base64
from fastapi.responses import Response
from report_pdf import build_report
import time
from stability_checker import StabilityChecker
from emissions_calculator import EmissionsCalculator
from database import load_bays_from_db, load_containers_from_db
from fastapi.middleware.cors import CORSMiddleware
from dataclasses import asdict
from fastapi import HTTPException
from pydantic import BaseModel, Field
from database import add_container_to_db, update_container_in_db, delete_container_from_db
from database import add_bay_section_to_db, remove_last_bay_section_from_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def build_demo_ship() -> Ship:
    ship = Ship(name="MV CargoOpt Demo")

    for bay in load_bays_from_db():
        ship.add_bay(bay)

    for container in load_containers_from_db():
        ship.add_container(container)

    return ship


@app.post("/optimize")
def optimize(distance_nm: float = 330, method: str = "ga"):
    method = method.lower()
    if method not in ("ga", "rl"):
        raise HTTPException(status_code=400, detail="method must be 'ga' or 'rl'")

    ship = build_demo_ship()
    if len(ship.containers_to_place) > len(ship.bays):
        raise HTTPException(
            status_code=400,
            detail=f"Not enough bays: {len(ship.containers_to_place)} containers but only {len(ship.bays)} bays",
        )

    start_time = time.time()
    scorer = GeneticOptimizer(ship)
    best_arrangement, best_score = None, float("-inf")
    if method == "ga":
        for _ in range(5):
            optimizer = GeneticOptimizer(ship, population_size=100, generations=200)
            arrangement, score = optimizer.run()
            if score > best_score:
                best_arrangement, best_score = arrangement, score
    else:
        best_arrangement, best_score = RLOptimizer(ship).run()

    violations = scorer.find_violations(best_arrangement)
    stability = StabilityChecker(ship, best_arrangement)
    balance = stability.check_port_starboard_balance()
    cog_height = stability.calculate_center_of_gravity_height()

    emissions = EmissionsCalculator(ship, voyage_distance_nm=distance_nm)

    containers_result = []
    for container_index, bay_index in enumerate(best_arrangement):
        container = ship.containers_to_place[container_index]
        bay = ship.bays[bay_index]
        containers_result.append({
            "container_id": container.container_id,
            "weight": container.weight,
            "length": container.length,
            "width": container.width,
            "height": container.height,
            "bay_id": bay.bay_id,
            "row": bay.row,
            "tier": bay.tier,
            "bay_number": bay.bay_number,
            "is_fragile": container.is_fragile,
            "is_hazardous": container.is_hazardous,
            "destination_port": container.destination_port,
        })

    return {
        "score": best_score,
        "method": method.upper(),
        "time_seconds": round(time.time() - start_time, 2),
        "violations": violations,
        "containers": containers_result,
        "sections": max(b.bay_number for b in ship.bays),
        "stability": {
            "left_weight_kg": balance["left_weight_kg"],
            "right_weight_kg": balance["right_weight_kg"],
            "imbalance_percent": balance["imbalance_percent"],
            "is_balanced": balance["is_balanced"],
            "center_of_gravity_height_m": cog_height,
        },
        "emissions": {
            "voyage_distance_nm": emissions.voyage_distance_nm,
            "total_cargo_tons": emissions.total_cargo_tons(),
            "fuel_kg": emissions.estimate_fuel_kg(),
            "co2_kg": emissions.estimate_co2_kg(),
            "cii_grade": emissions.cii_grade(),
        },
    }

class ContainerIn(BaseModel):
    container_id: str
    length: float = Field(gt=0, le=12.2)
    width: float = Field(gt=0, le=3)
    height: float = Field(gt=0, le=2.6)
    weight: float = Field(gt=0, le=30000)
    is_fragile: bool = False
    is_hazardous: bool = False
    destination_port: str = ""


class ContainerUpdate(BaseModel):
    length: float = Field(gt=0, le=12.2)
    width: float = Field(gt=0, le=3)
    height: float = Field(gt=0, le=2.6)
    weight: float = Field(gt=0, le=30000)
    is_fragile: bool = False
    is_hazardous: bool = False
    destination_port: str = ""


@app.get("/containers")
def list_containers():
    return [asdict(c) for c in load_containers_from_db()]


@app.post("/containers")
def create_container(container: ContainerIn):
    try:
        add_container_to_db(container.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"message": f"Container {container.container_id} added"}


@app.put("/containers/{container_id}")
def edit_container(container_id: str, container: ContainerUpdate):
    try:
        update_container_in_db(container_id, container.model_dump())
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {"message": f"Container {container_id} updated"}


@app.delete("/containers/{container_id}")
def remove_container(container_id: str):
    try:
        delete_container_from_db(container_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {"message": f"Container {container_id} removed"}

    if len(ship.containers_to_place) > len(ship.bays):
        raise HTTPException(
            status_code=400,
            detail=f"Not enough bays: {len(ship.containers_to_place)} containers but only {len(ship.bays)} bays",
        )

@app.get("/bays")
def bay_summary():
    bays = load_bays_from_db()
    sections = max((b.bay_number for b in bays), default=0)
    return {"sections": sections, "total_bays": len(bays)}


@app.post("/bays/section")
def add_section():
    try:
        new_section = add_bay_section_to_db()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"message": f"Section {new_section} added (6 new bays)"}


@app.delete("/bays/section")
def remove_section():
    try:
        removed = remove_last_bay_section_from_db()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"message": f"Section {removed} removed"}


def run_method(ship, method):
    start = time.time()
    if method == "ga":
        best, best_score = None, float("-inf")
        for _ in range(5):
            arrangement, score = GeneticOptimizer(ship, population_size=100, generations=200).run()
            if score > best_score:
                best, best_score = arrangement, score
    else:
        best, best_score = RLOptimizer(ship).run()
    return best, best_score, time.time() - start


class ScreenshotIn(BaseModel):
    title: str
    image: str


class ReportRequest(BaseModel):
    distance_nm: float = 330
    voyage_name: str = ""
    screenshots: list[ScreenshotIn] = []


@app.post("/report")
def make_report(req: ReportRequest):
    ship = build_demo_ship()
    if len(ship.containers_to_place) == 0:
        raise HTTPException(status_code=400, detail="No containers to report on")
    if len(ship.containers_to_place) > len(ship.bays):
        raise HTTPException(
            status_code=400,
            detail=f"Not enough bays: {len(ship.containers_to_place)} containers but only {len(ship.bays)} bays",
        )

    scorer = GeneticOptimizer(ship)
    ga_arr, ga_score, ga_time = run_method(ship, "ga")
    rl_arr, rl_score, rl_time = run_method(ship, "rl")
    used = "RL" if rl_score > ga_score else "GA"
    arrangement = rl_arr if used == "RL" else ga_arr

    stability = StabilityChecker(ship, arrangement)
    balance = stability.check_port_starboard_balance()
    cog_height = stability.calculate_center_of_gravity_height()
    emissions = EmissionsCalculator(ship, voyage_distance_nm=req.distance_nm)

    containers_result = []
    for container_index, bay_index in enumerate(arrangement):
        container = ship.containers_to_place[container_index]
        bay = ship.bays[bay_index]
        containers_result.append({
            "container_id": container.container_id,
            "weight": container.weight,
            "length": container.length,
            "width": container.width,
            "height": container.height,
            "row": bay.row,
            "tier": bay.tier,
            "bay_number": bay.bay_number,
            "is_fragile": container.is_fragile,
            "is_hazardous": container.is_hazardous,
            "destination_port": container.destination_port,
        })

    groups = {}
    for c in containers_result:
        port = (c["destination_port"] or "").strip().upper() or "NO PORT"
        groups.setdefault(port, []).append(c)

    def port_key(port):
        try:
            rank = scorer.port_rank(port)
        except Exception:
            rank = None
        return (rank is None, rank if rank is not None else 0, port)

    unload_plan = []
    for port in sorted(groups, key=port_key):
        items = sorted(groups[port], key=lambda c: (-c["tier"], c["bay_number"], c["row"]))
        unload_plan.append({"port": port, "containers": items})

    data = {
        "ship_name": ship.name,
        "voyage_name": req.voyage_name,
        "sections": max(b.bay_number for b in ship.bays),
        "n_bays": len(ship.bays),
        "n_containers": len(ship.containers_to_place),
        "used": used,
        "ga": {"score": ga_score, "seconds": ga_time, "violations": scorer.find_violations(ga_arr)},
        "rl": {"score": rl_score, "seconds": rl_time, "violations": scorer.find_violations(rl_arr)},
        "containers": containers_result,
        "unload_plan": unload_plan,
        "stability": {
            "left_weight_kg": balance["left_weight_kg"],
            "right_weight_kg": balance["right_weight_kg"],
            "imbalance_percent": balance["imbalance_percent"],
            "is_balanced": balance["is_balanced"],
            "center_of_gravity_height_m": cog_height,
        },
        "emissions": {
            "voyage_distance_nm": emissions.voyage_distance_nm,
            "total_cargo_tons": emissions.total_cargo_tons(),
            "fuel_kg": emissions.estimate_fuel_kg(),
            "co2_kg": emissions.estimate_co2_kg(),
            "cii_grade": emissions.cii_grade(),
        },
    }

    screenshots = []
    for shot in req.screenshots:
        if shot.image.startswith("data:image/png;base64,"):
            try:
                screenshots.append((shot.title, base64.b64decode(shot.image.split(",", 1)[1])))
            except Exception:
                pass

    pdf = build_report(data, screenshots)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Voyage report.pdf"'},
    )
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.campaigns.schemas import AssetResponse, CampaignResponse, FactResponse, FindingResponse
from app.core.db import get_db
from app.db.models import Asset, BrandGuidelineSource, Campaign, ExtractedFact, Finding, Organization, Scan, SourcePassage

router = APIRouter(tags=["sample-workspace"])


class SampleWorkspaceResponse(BaseModel):
    organization_name: str
    campaign: CampaignResponse
    assets: list[AssetResponse]
    findings: list[FindingResponse]
    facts: list[FactResponse]
    read_only: bool = True


@router.get("/sample-workspace", response_model=SampleWorkspaceResponse)
def get_sample_workspace(db: Session = Depends(get_db)):
    organization = db.scalar(select(Organization).where(Organization.is_sample.is_(True), Organization.verification_status == "approved").order_by(Organization.created_at).limit(1))
    if not organization:
        raise HTTPException(status_code=404, detail="The sample workspace has not been seeded for this environment.")
    campaign = db.scalar(select(Campaign).where(Campaign.organization_id == organization.id, Campaign.deleted_at.is_(None)).order_by(Campaign.created_at.desc()).limit(1))
    if not campaign:
        raise HTTPException(status_code=404, detail="The sample campaign is not available.")
    assets = db.scalars(select(Asset).where(Asset.organization_id == organization.id, Asset.campaign_id == campaign.id, Asset.current.is_(True), Asset.deleted_at.is_(None)).order_by(Asset.channel)).all()
    scan = db.scalar(select(Scan).where(Scan.organization_id == organization.id, Scan.campaign_id == campaign.id, Scan.status == "completed").order_by(Scan.created_at.desc()).limit(1))
    finding_rows = []
    fact_rows = []
    if scan:
        finding_rows = db.execute(select(Finding, SourcePassage, BrandGuidelineSource).outerjoin(SourcePassage, (SourcePassage.organization_id == Finding.organization_id) & (SourcePassage.id == Finding.source_passage_id)).outerjoin(BrandGuidelineSource, (BrandGuidelineSource.organization_id == SourcePassage.organization_id) & (BrandGuidelineSource.id == SourcePassage.source_id)).where(Finding.organization_id == organization.id, Finding.scan_id == scan.id).order_by(Finding.created_at)).all()
        fact_rows = db.execute(select(ExtractedFact, Asset.channel).join(Asset, (Asset.organization_id == ExtractedFact.organization_id) & (Asset.id == ExtractedFact.asset_id)).where(ExtractedFact.organization_id == organization.id, ExtractedFact.campaign_id == campaign.id, ExtractedFact.fact_type.in_(["percentage", "currency", "date", "claim"])).order_by(Asset.channel, ExtractedFact.fact_type)).all()
    findings = [FindingResponse.model_validate({**finding.__dict__, "source_title": source.title if source else None, "source_version": source.version if source else None, "source_page_number": passage.page_number if passage else None, "source_location_label": passage.location_label if passage else None, "source_text": passage.text if passage else None}) for finding, passage, source in finding_rows]
    facts = [FactResponse(id=fact.id, asset_id=fact.asset_id, channel=channel, fact_type=fact.fact_type, value=fact.value, asset_location=fact.asset_location, source_passage_id=fact.source_passage_id) for fact, channel in fact_rows]
    return SampleWorkspaceResponse(organization_name=organization.name, campaign=CampaignResponse.model_validate(campaign, from_attributes=True), assets=[AssetResponse.model_validate(asset, from_attributes=True) for asset in assets], findings=findings, facts=facts)

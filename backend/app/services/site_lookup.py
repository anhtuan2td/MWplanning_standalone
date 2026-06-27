from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.site import Site
from app.services.mw_links import band_for_site, height_for_site, links_for_site, other_site_code


def site_lookup(db: Session, site_code: str) -> str:
    code = "".join(site_code.upper().split())
    site = db.scalar(select(Site).where(func.upper(Site.site_code) == code))
    if site is None:
        return f"Không tìm thấy trạm {code} trong dữ liệu site."

    links = links_for_site(code)
    lines = [f"Thông tin trạm {site.site_code}:", f"- Tuyến MW: {len(links)}"]
    for link in links:
        other = other_site_code(link, code)
        band = band_for_site(link, code) or "không rõ band"
        lines.append(f"  - {code}-{other}: {band}, {link.distance_km:g} km, cao độ anten {height_for_site(link, code):g} m")

    cells_4g = "chưa có dữ liệu" if site.cells_4g is None else str(site.cells_4g)
    cells_5g = "chưa có dữ liệu" if site.cells_5g is None else str(site.cells_5g)
    lines.append(f"- Cell: 4G = {cells_4g}; 5G = {cells_5g}")
    lines.append(f"- Vu hồi: {'Có' if site.diverse_routing else 'Chưa'}")
    lines.append(f"- Overload: {'Có' if site.overload > 0 else 'Không'}; hệ số = {site.overload}")
    return "\n".join(lines)

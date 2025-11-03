"""Cloud streaming service registry for WomCast.

Provides deep links to legal streaming services (Netflix, Disney+, HBO Max, etc.)
without any DRM bypass. Users can scan QR codes to open content in native apps.

Legal compliance:
- NO DRM circumvention or decryption
- NO unauthorized access to paid content
- NO piracy or terms-of-service violations
- Only provides deep links to official apps
- Respects all content provider terms of service
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CloudProvider(str, Enum):
    """Supported cloud streaming providers."""

    NETFLIX = "netflix"
    DISNEY_PLUS = "disney_plus"
    HBO_MAX = "hbo_max"
    AMAZON_PRIME = "amazon_prime"
    HULU = "hulu"
    APPLE_TV_PLUS = "apple_tv_plus"
    PEACOCK = "peacock"
    PARAMOUNT_PLUS = "paramount_plus"
    YOUTUBE = "youtube"
    YOUTUBE_TV = "youtube_tv"


@dataclass
class CloudService:
    """Cloud streaming service metadata."""

    provider: CloudProvider
    name: str
    description: str
    icon_url: str
    requires_subscription: bool
    deep_link_template: str  # Template for native app deep links
    web_url_template: str  # Template for web browser fallback
    regions: list[str]  # ISO country codes (e.g., ["US", "CA", "GB"])


# Cloud service registry
CLOUD_SERVICES: dict[CloudProvider, CloudService] = {
    CloudProvider.NETFLIX: CloudService(
        provider=CloudProvider.NETFLIX,
        name="Netflix",
        description="Stream movies, TV shows, and originals",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/netflix.png",
        requires_subscription=True,
        deep_link_template="netflix://title/{title_id}",
        web_url_template="https://www.netflix.com/title/{title_id}",
        regions=["US", "CA", "GB", "AU", "DE", "FR", "ES", "IT", "JP", "BR", "MX", "IN"],
    ),
    CloudProvider.DISNEY_PLUS: CloudService(
        provider=CloudProvider.DISNEY_PLUS,
        name="Disney+",
        description="Disney, Pixar, Marvel, Star Wars, National Geographic",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/disney-plus.png",
        requires_subscription=True,
        deep_link_template="disneyplus://content/{content_id}",
        web_url_template="https://www.disneyplus.com/video/{content_id}",
        regions=["US", "CA", "GB", "AU", "NZ", "DE", "FR", "ES", "IT", "NL", "SE", "NO"],
    ),
    CloudProvider.HBO_MAX: CloudService(
        provider=CloudProvider.HBO_MAX,
        name="HBO Max",
        description="HBO originals, Warner Bros. movies, and more",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/hbo-max.png",
        requires_subscription=True,
        deep_link_template="hbomax://content/{content_id}",
        web_url_template="https://www.hbomax.com/series/{content_id}",
        regions=["US", "CA", "MX", "BR", "AR", "CL", "CO"],
    ),
    CloudProvider.AMAZON_PRIME: CloudService(
        provider=CloudProvider.AMAZON_PRIME,
        name="Amazon Prime Video",
        description="Prime Video originals and licensed content",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/prime-video.png",
        requires_subscription=True,
        deep_link_template="aiv://aiv/view?gti={content_id}",
        web_url_template="https://www.amazon.com/gp/video/detail/{content_id}",
        regions=["US", "CA", "GB", "DE", "FR", "ES", "IT", "JP", "IN", "AU", "BR", "MX"],
    ),
    CloudProvider.HULU: CloudService(
        provider=CloudProvider.HULU,
        name="Hulu",
        description="Current TV episodes, movies, and originals",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/hulu.png",
        requires_subscription=True,
        deep_link_template="hulu://watch/{content_id}",
        web_url_template="https://www.hulu.com/watch/{content_id}",
        regions=["US", "JP"],
    ),
    CloudProvider.APPLE_TV_PLUS: CloudService(
        provider=CloudProvider.APPLE_TV_PLUS,
        name="Apple TV+",
        description="Apple Originals and exclusive content",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/apple-tv.png",
        requires_subscription=True,
        deep_link_template="com.apple.tv://tv.apple.com/show/{content_id}",
        web_url_template="https://tv.apple.com/show/{content_id}",
        regions=["US", "CA", "GB", "AU", "DE", "FR", "ES", "IT", "JP", "KR", "CN", "IN"],
    ),
    CloudProvider.PEACOCK: CloudService(
        provider=CloudProvider.PEACOCK,
        name="Peacock",
        description="NBCUniversal content with free and premium tiers",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/peacock.png",
        requires_subscription=False,  # Has free tier
        deep_link_template="peacock://watch/{content_id}",
        web_url_template="https://www.peacocktv.com/watch/{content_id}",
        regions=["US"],
    ),
    CloudProvider.PARAMOUNT_PLUS: CloudService(
        provider=CloudProvider.PARAMOUNT_PLUS,
        name="Paramount+",
        description="CBS, MTV, Nickelodeon, and Paramount content",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/paramount-plus.png",
        requires_subscription=True,
        deep_link_template="paramountplus://content/{content_id}",
        web_url_template="https://www.paramountplus.com/shows/{content_id}",
        regions=["US", "CA", "AU", "GB", "DE", "FR", "IT", "ES", "MX", "BR"],
    ),
    CloudProvider.YOUTUBE: CloudService(
        provider=CloudProvider.YOUTUBE,
        name="YouTube",
        description="Free and premium video content",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/youtube.png",
        requires_subscription=False,
        deep_link_template="vnd.youtube://www.youtube.com/watch?v={video_id}",
        web_url_template="https://www.youtube.com/watch?v={video_id}",
        regions=["*"],  # Global availability
    ),
    CloudProvider.YOUTUBE_TV: CloudService(
        provider=CloudProvider.YOUTUBE_TV,
        name="YouTube TV",
        description="Live TV streaming with major networks",
        icon_url="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/youtube-tv.png",
        requires_subscription=True,
        deep_link_template="https://tv.youtube.com/watch/{program_id}",
        web_url_template="https://tv.youtube.com/watch/{program_id}",
        regions=["US"],
    ),
}


@dataclass
class CloudLink:
    """Deep link and metadata for cloud service content."""

    provider: CloudProvider
    title: str
    content_id: str
    deep_link: str  # Native app URL
    web_link: str  # Browser fallback URL
    qr_code_url: str | None = None  # QR code image URL (generated on-demand)


def get_all_services() -> list[CloudService]:
    """Get all registered cloud services.

    Returns:
        List of CloudService objects sorted by name
    """
    return sorted(CLOUD_SERVICES.values(), key=lambda s: s.name)


def get_service(provider: CloudProvider) -> CloudService | None:
    """Get cloud service by provider ID.

    Args:
        provider: CloudProvider enum value

    Returns:
        CloudService object or None if not found
    """
    return CLOUD_SERVICES.get(provider)


def is_available_in_region(provider: CloudProvider, region: str) -> bool:
    """Check if a cloud service is available in a specific region.

    Args:
        provider: CloudProvider enum value
        region: ISO country code (e.g., "US", "GB")

    Returns:
        True if service is available in the region
    """
    service = get_service(provider)
    if not service:
        return False

    # "*" means globally available
    if "*" in service.regions:
        return True

    return region.upper() in service.regions


def create_cloud_link(
    provider: CloudProvider, title: str, content_id: str
) -> CloudLink | None:
    """Create a cloud link with deep link and web fallback.

    Args:
        provider: CloudProvider enum value
        title: Human-readable title for the content
        content_id: Provider-specific content identifier

    Returns:
        CloudLink object or None if provider not found
    """
    service = get_service(provider)
    if not service:
        return None

    # Generate deep link from template
    deep_link = service.deep_link_template.format(
        title_id=content_id,
        content_id=content_id,
        video_id=content_id,
        program_id=content_id,
    )

    # Generate web fallback from template
    web_link = service.web_url_template.format(
        title_id=content_id,
        content_id=content_id,
        video_id=content_id,
        program_id=content_id,
    )

    # Generate QR code URL
    qr_code_url = f"/v1/cloud/qr?provider={provider.value}&content_id={content_id}"

    return CloudLink(
        provider=provider,
        title=title,
        content_id=content_id,
        deep_link=deep_link,
        web_link=web_link,
        qr_code_url=qr_code_url,
    )


if __name__ == "__main__":
    # Example usage for testing
    print("WomCast Cloud Service Registry\n")

    print(f"Total services: {len(CLOUD_SERVICES)}\n")

    for service in get_all_services():
        print(f"📺 {service.name}")
        print(f"   Provider: {service.provider.value}")
        print(f"   Description: {service.description}")
        print(f"   Subscription required: {service.requires_subscription}")
        print(f"   Regions: {', '.join(service.regions)}")
        print()

    # Test link creation
    print("\nExample: Creating Netflix link")
    link = create_cloud_link(CloudProvider.NETFLIX, "Stranger Things", "80057281")
    if link:
        print(f"Title: {link.title}")
        print(f"Deep link: {link.deep_link}")
        print(f"Web link: {link.web_link}")

    # Test region availability
    print("\n\nRegion availability check:")
    print(f"Netflix in US: {is_available_in_region(CloudProvider.NETFLIX, 'US')}")
    print(f"Hulu in GB: {is_available_in_region(CloudProvider.HULU, 'GB')}")
    print(f"YouTube in JP: {is_available_in_region(CloudProvider.YOUTUBE, 'JP')}")

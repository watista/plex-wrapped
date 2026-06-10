from app.tautulli.client import TautulliError
from app.tautulli.devices import collect_unique_devices


class FakeTautulli:
    def get_users(self):
        return [
            {"user_id": 1, "friendly_name": "Alice"},
            {"user_id": 2, "username": "bob"},
        ]

    def get_user_player_stats(self, user_id):
        if user_id == 1:
            return [
                {
                    "player_name": "Apple TV",
                    "platform": "tvOS",
                    "platform_name": "Apple TV",
                    "total_plays": 10,
                },
                {
                    "player_name": "iPhone",
                    "platform": "iOS",
                    "platform_name": "iPhone",
                    "total_plays": 5,
                },
            ]
        return [
            {
                "player_name": "Apple TV",
                "platform": "tvOS",
                "platform_name": "Apple TV",
                "total_plays": 3,
            },
            {
                "player_name": "Chrome",
                "platform": "Chrome",
                "platform_name": "Chrome",
                "total_plays": 7,
            },
        ]


def test_collect_unique_devices_merges_across_users():
    result = collect_unique_devices(FakeTautulli())

    assert result["count"] == 3
    assert result["names"] == ["Apple TV", "Chrome", "iPhone"]

    apple_tv = next(item for item in result["devices"] if item["name"] == "Apple TV")
    assert apple_tv["total_plays"] == 13
    assert apple_tv["users"] == ["Alice", "bob"]
    assert apple_tv["platform"] == "tvOS"


def test_collect_unique_devices_skips_users_with_errors():
    class PartialTautulli(FakeTautulli):
        def get_user_player_stats(self, user_id):
            if user_id == 2:
                raise TautulliError("unavailable")
            return super().get_user_player_stats(user_id)

    result = collect_unique_devices(PartialTautulli())

    assert result["count"] == 2
    assert result["names"] == ["Apple TV", "iPhone"]
    apple_tv = next(item for item in result["devices"] if item["name"] == "Apple TV")
    assert apple_tv["users"] == ["Alice"]

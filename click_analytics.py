"""
Модуль анализа кликов для тестирования фишинга
Анализирует метрики кликов: общее количество ссылок, клики, соотношения и проценты
"""


class ClickAnalytics:
    """Класс для анализа статистики кликов"""
    
    def __init__(self, campaign_data: dict):
        """
        Инициализация анализатора кликов
        
        Args:
            campaign_data: словарь с данными кампании
                {
                    'total_links': int,           # общее количество уникальных ссылок в кампании
                    'total_clicks': int,          # общее количество кликов (может быть > total_links)
                    'unique_clicked_links': int   # количество ссылок с хотя бы одним кликом
                }
        """
        self.total_links = campaign_data.get('total_links', 0)
        self.total_clicks = campaign_data.get('total_clicks', 0)
        self.unique_clicked_links = campaign_data.get('unique_clicked_links', 0)
    
    def get_total_links(self) -> int:
        """Возвращает общее количество ссылок"""
        return self.total_links
    
    def get_total_clicks(self) -> int:
        """Возвращает общее количество кликов"""
        return self.total_clicks
    
    def get_click_ratio(self) -> float:
        """
        Возвращает соотношение кликов к ссылкам
        
        Returns:
            float: отношение кликов к ссылкам (клики/ссылки)
        """
        if self.total_links == 0:
            return 0.0
        return round(self.total_clicks / self.total_links, 2)
    
    def get_click_percentage(self) -> float:
        """
        Возвращает процентное соотношение общего числа кликов к общему числу ссылок.

        Если кликов больше, чем ссылок, процент может превышать 100%.

        Returns:
            float: процент кликов (может быть >100) — (total_clicks / total_links) * 100
        """
        if self.total_links == 0:
            return 0.0
        return round((self.total_clicks / self.total_links) * 100, 2)
    
    def get_analytics_report(self) -> dict:
        """
        Возвращает полный отчет анализа кликов
        
        Returns:
            dict: словарь со всеми метриками
        """
        non_clicked = self.total_links - self.unique_clicked_links
        
        return {
            'total_links': self.total_links,
            'total_clicks': self.total_clicks,
            'unique_clicked_links': self.unique_clicked_links,
            'click_ratio': self.get_click_ratio(),
            'click_percentage': self.get_click_percentage(),
            'non_clicked': non_clicked
        }
    
    def print_analytics_report(self) -> None:
        """Выводит отчет анализа кликов в консоль"""
        report = self.get_analytics_report()
        
        print("\n" + "="*50)
        print("ОТЧЕТ АНАЛИЗА КЛИКОВ")
        print("="*50)
        print(f"Общее количество ссылок:        {report['total_links']}")
        print(f"Общее количество кликов:        {report['total_clicks']}")
        print(f"Ссылок с кликами:               {report['unique_clicked_links']}")
        print(f"Не открыто ссылок:              {report['non_clicked']}")
        print(f"Соотношение клики/ссылки:       {report['click_ratio']}")
        print(f"Процент ссылок с кликами:       {report['click_percentage']}%")
        print("="*50 + "\n")


def analyze_multiple_campaigns(campaigns: list) -> dict:
    """
    Анализирует статистику через несколько кампаний
    
    Args:
        campaigns: список словарей с данными кампаний
        
    Returns:
        dict: агрегированная статистика
    """
    total_links_all = 0
    total_clicks_all = 0
    
    for campaign in campaigns:
        total_links_all += campaign.get('total_links', 0)
        total_clicks_all += campaign.get('total_clicks', 0)
    
    analytics = ClickAnalytics({
        'total_links': total_links_all,
        'total_clicks': total_clicks_all
    })
    
    return {
        'campaign_count': len(campaigns),
        'total_links': total_links_all,
        'total_clicks': total_clicks_all,
        'overall_ratio': analytics.get_click_ratio(),
        'overall_percentage': analytics.get_click_percentage()
    }


# Пример использования
if __name__ == "__main__":
    # Пример 1: анализ одной кампании
    campaign_data = {
        'total_links': 100,
        'total_clicks': 25
    }
    
    analytics = ClickAnalytics(campaign_data)
    analytics.print_analytics_report()
    
    # Пример 2: анализ нескольких кампаний
    campaigns = [
        {'total_links': 100, 'total_clicks': 25},
        {'total_links': 150, 'total_clicks': 45},
        {'total_links': 80, 'total_clicks': 20}
    ]
    
    multi_report = analyze_multiple_campaigns(campaigns)
    print("\nОТЧЕТ ПО ВСЕМ КАМПАНИЯМ")
    print("="*50)
    for key, value in multi_report.items():
        if isinstance(value, float):
            print(f"{key}: {value}")
        else:
            print(f"{key}: {value}")
    print("="*50)

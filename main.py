import csv
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from decorator import retry_on_failure


class Client:
    def __init__(self, store_id, in_stock: str, url: str):
        self.store_id = store_id
        self.session = requests.Session()
        self.session.headers = {
            "User-Agent": UserAgent().random,
            "cookie": f"metroStoreId={self.store_id}; is18Confirmed=true;"
        }

        self.in_stock = in_stock
        self.url = url
        self.url_product = "https://online.metro-cc.ru"

        self.library = {
            "id_product": [],
            "product_name": [],
            "product_link": [],
            "regular_price": [],
            "promo_price": [],
            "brand": []
        }

    def get_page_content(self, url, params=None):
        if params is None:
            params = {"in_stock": "", "page": ""}
        res = self.session.get(url, params=params)
        res.raise_for_status()
        return res

    def load_page_category(self, in_stock: str = "", page: str = ""):
        params = {"in_stock": in_stock, "page": page}
        return self.get_page_content(self.url, params=params)

    def get_pagination_limit(self, soup):
        return int(soup.select('#catalog-wrapper > main > div:nth-child(2) > nav > ul')[0].contents[-2].text)

    @retry_on_failure(max_retries=3, delay=1)
    def get_brand_product(self, url_product):
        product_page = self.get_page_content(url_product)
        soup = BeautifulSoup(product_page.content, "lxml")

        product_attribute = soup.find(
            name="ul",
            attrs={
                "class": "product-attributes__list style--product-page-short-list"
            }
        )

        if len(product_attribute.contents) < 8:
            brand = product_attribute.contents[2].contents[4].text.replace("\n", "").strip()
        else:
            brand = product_attribute.contents[8].contents[4].text.replace("\n", "").strip()

        return brand

    def get_product_name(self, soup_obj):
        product_name = soup_obj.find(
            name="span",
            attrs={"class": "product-card-name__text"}
        )
        return product_name.contents[0].replace("\n", "").strip()

    def get_url_product(self, soup_obj):
        url_product = self.url_product + soup_obj.find(
            name="a",
            attrs={
                "data-gtm": "product-card-name"
            }
        ).attrs["href"]
        return url_product

    def get_price_product(self, soup_obj, class_tag):
        price_tag = soup_obj.find(
            name="div",
            attrs={
                "class": class_tag
            }
        )
        try:
            price_rub_penny = [
                price_tag.find(name="span", attrs={"class": "product-price__sum-rubles"}),
                price_tag.find(name="span", attrs={"class": "product-price__sum-penny"})
            ]
        except Exception:
            return ""

        return "".join([x.text for x in price_rub_penny if x is not None])

    def save_result(self):
        keys = list(self.library.keys())
        values = list(self.library.values())
        with open(f"result_{self.store_id}.csv", "w",  newline='') as f:
            csv_obj = csv.writer(f, delimiter=',', )
            csv_obj.writerow(keys)
            csv_obj.writerows(zip(*values))

    def parse_page(self):
        page_catalog = self.load_page_category(in_stock=self.in_stock)
        soup = BeautifulSoup(page_catalog.content, "lxml")
        try:
            pagination_limit = self.get_pagination_limit(soup)
            for page in range(pagination_limit):
                print("Cтраница ", page+1)
                if page != 0:
                    page_catalog = self.load_page_category(in_stock=self.in_stock, page=str(page + 1))
                    soup = BeautifulSoup(page_catalog.content, "lxml")

                elements = soup.select('#products-inner')[0].contents
                if " " not in elements:
                    for elem in elements:
                        print("#"*50)
                        self.library["id_product"].append(elem.attrs["id"])
                        print(elem.attrs["id"])

                        self.library["product_name"].append(self.get_product_name(elem))
                        print(self.library["product_name"][-1])

                        self.library["product_link"].append(self.get_url_product(elem))
                        print(self.library["product_link"][-1])

                        self.library["brand"].append(self.get_brand_product(self.library["product_link"][-1]))
                        print(self.library["brand"][-1])

                        actual_price = self.get_price_product(soup_obj=elem, class_tag="product-unit-prices__actual-wrapper")
                        print(actual_price)
                        old_price = self.get_price_product(soup_obj=elem, class_tag="product-unit-prices__old-wrapper")
                        print(old_price)
                        print("#" * 50)
                        if old_price:
                            self.library["regular_price"].append(
                                old_price.strip().replace('\xa0', '')
                            )
                            self.library["promo_price"].append(
                                actual_price.strip().replace('\xa0', '')
                            )
                        else:
                            self.library["regular_price"].append(
                                actual_price.strip().replace('\xa0', '')
                            )
                            self.library["promo_price"].append("")
                else:
                    continue
            self.save_result()

        except Exception as e:
            print(e)


if __name__ == "__main__":
    metro_store_id = {
        "MSK": "13",
        "SPB": "16"
    }

    client = Client(
        store_id=metro_store_id["SPB"],
        in_stock="1",
        url=f"https://online.metro-cc.ru/category/alkogolnaya-produkciya/pivo-sidr"
    )

    client.parse_page()

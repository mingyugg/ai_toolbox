import os
import bs4
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('BASE_URL'),
)

system_prompt = """
    你是一位{{role}}, 请仔细阅读用户提供的<githup trending list>里面的每一个仓库信息，推荐你觉得你认为你最感兴趣的仓库,请给出你推荐的理由(reason)以及这个仓库能给你点来什么好处(benefit)
    <注意事项>
    1、你的回答必须使用中文回答
    2、回答的格式，必须遵守EXAMPLE JSON OUTPUT
    </注意事项>
"""
system_prompt1 = """
    EXAMPLE JSON OUTPUT:
    {
        "rep_name": xxx,
        "reason": "",
        "rep_url": rep_url,
        "star": star,
        "benefit": "",
    }
"""
user_prompt = "这是一份<githup trending list>{githup_trending_list}</githup trending list>"
roles = ['10年资深程序员', '产品经理', '经验丰富的架构师']


def get_trending_list(since='weekly') -> list:
    trending_list = []

    url = f'https://github.com/trending?since={since}'
    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.content, 'lxml')
    article_box_rows = soup.find_all('article', class_='Box-row')
    for article_tag in article_box_rows:
        rep_name = article_tag.find('h2').text
        if not rep_name:
            continue
        rep_name = rep_name.strip().replace('\n', '').replace(' ', '')
        
        rep_desc = article_tag.find('p').text.strip()

        lang_span = article_tag.find('span', itemprop="programmingLanguage")
        lang = lang_span.text if lang_span else ''

        star_a = article_tag.find('a', href=f'/{rep_name}/stargazers')
        star = star_a.text.strip().replace(',', '')
        
        fork_a = article_tag.find('a', href=f'/{rep_name}/forks')
        fork = fork_a.text.strip().replace(',', '')
        trending_list.append(
            {
                'since': since,
                'rep_name': rep_name,
                'rep_url': f'https://github.com/{rep_name}',
                'rep_desc': rep_desc,
                'lang': lang,
                'star': star,
                'fork': fork
            }
        )
    return trending_list


def role_agent(githup_trending_list: list, role: str = '程序员'):
    messages = [
        {"role": "system", "content": system_prompt.format(role=role) + system_prompt1},
        {"role": "user", "content": user_prompt.format(githup_trending_list=githup_trending_list)}
    ]

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        response_format={
            'type': 'json_object'
        }
    )

    return json.loads(response.choices[0].message.content)


def generate_report_agent(githup_trending_list):
    recomm_data = []
    for role in roles:
        res = role_agent(githup_trending_list, role)
        res.update({'role': role})
        recomm_data.append(res)
        print(res)


def main():
    daliy_trending_list = get_trending_list()

    generate_report_agent(daliy_trending_list)


if __name__ == '__main__':
    main()

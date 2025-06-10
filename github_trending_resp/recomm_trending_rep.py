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

roles = ['10年经验的前端开发工程师', '10年经验的后端开发工程师']


def get_trending_list(since='daily') -> list:
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
                'fork': fork,
                f'{since}_star': article_tag.find_all('span')[-1].text.strip()
            }
        )
    return trending_list


def role_agent(githup_trending_list: list, role: str = '10年资深程序员序员'):
    system_prompt = """
        你是一位{role}, 请仔细阅读用户提供的<githup trending list>里面的每一个仓库的详情信息，并且结合你自身的特点和技术栈，推荐你觉得你认为你最感兴趣的三个仓库；
        并且给出你推荐的理由(reason)，以及这个仓库能给你点来什么好处(benefit)，推荐指数💖（recomm_star最高五星）
        <注意事项>
        1、你的回答必须使用中文回答
        2、回答的格式, 必须遵守<EXAMPLE JSON OUTPUT>, 不要有多余的字段输出, 确保输出的是一个数组
        </注意事项>
    """
    system_prompt1 = """
        <EXAMPLE JSON OUTPUT>:
            {
                "recommendations": [
                    {
                        "rep_name": xxx,
                        "reason": "",
                        "rep_url": rep_url,
                        "star": star,
                        "benefit": "",
                        "recomm_star": 💖
                    }
                ]
            }
        </EXAMPLE JSON OUTPUT>
    """
    user_prompt = "这是一份<githup trending list>{githup_trending_list}</githup trending list>"

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
    recomm_data = {}
    for role in roles:
        res = role_agent(githup_trending_list, role)
        recomm_data[role] = res
    recomm_data['githup_trending_list'] = githup_trending_list

    system_prompt = """
        根据用户提供输入数据, 输出markdown格式
        <markdown格式>
            # 今日Github热门仓库推荐
            如果让AI分别扮演 `后端开发人员`和`前端开发人员`，然后看看他们分别对`github每天的trending仓库`感兴趣的有哪些，并且给出他感兴趣的理由，那会发生什么呢？

            _本内容通过Python + AI生成，[项目地址跳转](https://github.com/mingyugg/ai_toolbox)_

            ---

            ## 后端开发人员推荐
            格式化"后端开发人员推荐"
            - 仓库名称：
            - 仓库推荐理由：
            - 推荐指数：
            - 仓库地址：
            多个仓库的话用"---"分割

            ## 前端开发人员推荐
            格式化"前端开发人员推荐"
            - 仓库名称：
            - 仓库推荐理由：
            - 推荐指数：
            - 仓库地址：
            多个仓库的话用"---"分割

            ## 强烈推荐
            如果发现该仓库前端和后端都推荐的话，可以把该仓库出现在这里，多个仓库的的话用"---"分开显示，没有的话就不用显示

            ## 今日Github Trending 列表
            格式化"githup_trending_list"
            <格式要求>
            1、生成markdown的table格式,对应的title为(
                rep_name->仓库,
                rep_url->仓库地址（转成地址，列入[仓库地址](rep_url)),
                rep_desc->仓库介绍（转化为中文输出）,
                lang->开发语言,
                star->star,
                fork->forks,
                {since}_star->{since}_star
            ),
            2、按照{since}_star获取的星星数进行排序
            </格式要求>


        </markdown格式>
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(recomm_data)}
    ]
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
    )
    print(response.choices[0].message.content)
    with open(
        os.path.join(os.path.dirname(__name__), 'recomm_file', 'test.md'),
        'w',
        encoding='utf-8'
    ) as fp:
        fp.write(response.choices[0].message.content)

    return recomm_data


def main():
    daliy_trending_list = get_trending_list()

    generate_report_agent(daliy_trending_list)


if __name__ == '__main__':
    main()

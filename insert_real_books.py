#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为图书馆系统添加真实的图书数据
每个分类生成10本图书
"""

import sqlite3
import os

# 数据库路径
DATABASE = 'library.db'

# 真实图书数据 - 每个分类10本
real_books = {
    '计算机': [
        {
            'isbn': '978-7-111-54930-6',
            'title': 'Python编程：从入门到实践',
            'author': 'Eric Matthes',
            'category': '计算机',
            'description': '本书是一本针对所有层次的Python读者而作的Python编程书籍。书中包含大量练习，帮助读者掌握Python编程技能。适合初学者和有一定基础的读者。',
            'publisher': '人民邮电出版社',
            'publish_date': '2020-05-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-54802-9',
            'title': 'Flask Web开发：基于Python的Web应用开发实战',
            'author': 'Miguel Grinberg',
            'category': '计算机',
            'description': '本书是Flask框架的权威指南，详细介绍了如何使用Flask开发Web应用。涵盖了从基础到高级的所有主题。',
            'publisher': '人民邮电出版社',
            'publish_date': '2018-06-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-54493-7',
            'title': '深入理解计算机系统',
            'author': 'Randal E. Bryant',
            'category': '计算机',
            'description': '本书从程序员的视角详细阐述计算机系统的本质概念，包括数据表示、程序的机器级表示、处理器体系结构等。是计算机科学领域的经典教材。',
            'publisher': '机械工业出版社',
            'publish_date': '2016-11-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-53783-4',
            'title': '算法导论（原书第3版）',
            'author': 'Thomas H. Cormen',
            'category': '计算机',
            'description': '本书是算法领域的经典教材，全面介绍了算法设计与分析的基本方法。包含了大量的算法实例和习题，适合计算机专业学生和从业者。',
            'publisher': '机械工业出版社',
            'publish_date': '2013-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-54260-3',
            'title': '设计模式：可复用面向对象软件的基础',
            'author': 'Erich Gamma',
            'category': '计算机',
            'description': '本书是软件工程领域的经典著作，详细介绍了23种设计模式。每种模式都配有详细的说明和代码示例，是面向对象编程的必读书籍。',
            'publisher': '机械工业出版社',
            'publish_date': '2000-09-01',
            'total_copies': 2,
            'available_copies': 2,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-115-35708-5',
            'title': '代码整洁之道',
            'author': 'Robert C. Martin',
            'category': '计算机',
            'description': '本书提出了编写高质量代码的原则和方法，帮助开发者编写出更清晰、更易于维护的代码。是软件工程领域的经典之作。',
            'publisher': '人民邮电出版社',
            'publish_date': '2011-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-52166-4',
            'title': '重构：改善既有代码的设计',
            'author': 'Martin Fowler',
            'category': '计算机',
            'description': '本书详细介绍了代码重构的原则、方法和技巧。通过大量的实例，展示了如何改善代码的结构和设计。',
            'publisher': '人民邮电出版社',
            'publish_date': '2010-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-52659-9',
            'title': '人月神话',
            'author': 'Frederick P. Brooks Jr.',
            'category': '计算机',
            'description': '本书是软件工程领域的经典著作，探讨了软件开发中的管理问题。提出了著名的"人月"概念，对软件项目管理有重要启示。',
            'publisher': '清华大学出版社',
            'publish_date': '2002-01-01',
            'total_copies': 2,
            'available_copies': 2,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-53825-6',
            'title': '黑客与画家',
            'author': 'Paul Graham',
            'category': '计算机',
            'description': '本书探讨了黑客文化和计算机编程的本质。作者以独特的视角分析了程序员的工作方式和思维方式。',
            'publisher': '人民邮电出版社',
            'publish_date': '2013-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-111-54928-5',
            'title': '代码大全',
            'author': 'Steve McConnell',
            'category': '计算机',
            'description': '本书是软件开发的百科全书，涵盖了软件开发的各个方面。从代码编写到项目管理，内容全面而深入。',
            'publisher': '电子工业出版社',
            'publish_date': '2006-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        }
    ],
    '文学': [
        {
            'isbn': '978-7-02-025344-7',
            'title': '活着',
            'author': '余华',
            'category': '文学',
            'description': '本书讲述了农村人福贵悲惨的人生遭遇。通过福贵一生的经历，反映了中国农村在几十年间的巨大变迁。',
            'publisher': '作家出版社',
            'publish_date': '1993-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025345-4',
            'title': '百年孤独',
            'author': '加西亚·马尔克斯',
            'category': '文学',
            'description': '本书描写了布恩迪亚家族七代人的传奇故事，以及加勒格勒根小镇百年的兴衰，反映了拉丁美洲一个世纪以来风云变幻的历史。',
            'publisher': '南海出版公司',
            'publish_date': '1967-05-30',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025346-1',
            'title': '围城',
            'author': '钱钟书',
            'category': '文学',
            'description': '本书以幽默的笔调，讲述了方鸿渐在欧洲留学期间的生活经历。通过方鸿渐与几位女性的感情纠葛，揭示了人生的荒诞和无奈。',
            'publisher': '人民文学出版社',
            'publish_date': '1947-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025347-8',
            'title': '红楼梦',
            'author': '曹雪芹',
            'category': '文学',
            'description': '本书是中国古典四大名著之一，以贾宝玉、林黛玉、薛宝钗的爱情婚姻悲剧为主线，展现了封建社会的衰落过程。',
            'publisher': '人民文学出版社',
            'publish_date': '1791-01-01',
            'total_copies': 6,
            'available_copies': 6,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025348-5',
            'title': '西游记',
            'author': '吴承恩',
            'category': '文学',
            'description': '本书是中国古典四大名著之一，讲述了唐僧师徒四人西天取经的故事。通过九九八十一难，展现了取经路上的艰辛和坚持。',
            'publisher': '人民文学出版社',
            'publish_date': '1592-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025349-2',
            'title': '三国演义',
            'author': '罗贯中',
            'category': '文学',
            'description': '本书是中国古典四大名著之一，讲述了东汉末年到西晋初年近百年的历史风云。通过魏蜀吴三国的兴衰，展现了历史的宏大画卷。',
            'publisher': '人民文学出版社',
            'publish_date': '1522-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025350-9',
            'title': '水浒传',
            'author': '施耐庵',
            'category': '文学',
            'description': '本书是中国古典四大名著之一，讲述了北宋末年以宋江为首的108位好汉在梁山泊起义的故事。展现了农民起义的悲壮历程。',
            'publisher': '人民文学出版社',
            'publish_date': '1589-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025351-6',
            'title': '平凡的世界',
            'author': '路遥',
            'category': '文学',
            'description': '本书以中国70年代中期到80年代中期为背景，以孙少安和孙少平两兄弟为中心，刻画了当时社会各阶层众多普通人的形象。',
            'publisher': '人民文学出版社',
            'publish_date': '1986-12-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-02-025352-3',
            'title': '呐喊',
            'author': '鲁迅',
            'category': '文学',
            'description': '本书是鲁迅的短篇小说集，收录了《狂人日记》、《孔乙己》、《药》等名篇。深刻揭示了封建社会的黑暗和人民的苦难。',
            'publisher': '人民文学出版社',
            'publish_date': '1923-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        }
    ],
    '历史': [
        {
            'isbn': '978-7-101-09547-2',
            'title': '万历十五年',
            'author': '黄仁宇',
            'category': '历史',
            'description': '本书以1587年为起点，讲述了明朝万历皇帝朱翊钧在位期间的历史。通过大历史观，揭示了明朝衰落的深层原因。',
            'publisher': '中华书局',
            'publish_date': '1982-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09548-9',
            'title': '明朝那些事儿',
            'author': '当年明月',
            'category': '历史',
            'description': '本书以幽默的笔调，讲述了明朝三百年的历史。通过现代人的视角，重新解读了明朝的历史事件和人物。',
            'publisher': '浙江人民出版社',
            'publish_date': '2006-03-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09549-6',
            'title': '中国大历史',
            'author': '吕思勉',
            'category': '历史',
            'description': '本书以时间为线索，系统梳理了中国五千年的历史。从远古时代到现代，全面展现了中国历史的发展脉络。',
            'publisher': '上海人民出版社',
            'publish_date': '2013-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09550-3',
            'title': '资治通鉴',
            'author': '司马光',
            'category': '历史',
            'description': '本书是中国古代著名的编年体通史，记载了从战国到五代共1362年的历史。是研究中国古代历史的重要资料。',
            'publisher': '中华书局',
            'publish_date': '1084-01-01',
            'total_copies': 6,
            'available_copies': 6,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09551-0',
            'title': '史记',
            'author': '司马迁',
            'category': '历史',
            'description': '本书是中国第一部纪传体通史，记载了上至黄帝下至汉武帝太初年间共3000多年的历史。被誉为"史家之绝唱，无韵之离骚"。',
            'publisher': '中华书局',
            'publish_date': '公元前91年',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09552-7',
            'title': '汉书',
            'author': '班固',
            'category': '历史',
            'description': '本书是中国第一部纪传体断代史，记载了西汉一朝230年的历史。与《史记》、《后汉书》、《三国志》合称"前四史"。',
            'publisher': '中华书局',
            'publish_date': '公元83年',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09553-4',
            'title': '后汉书',
            'author': '范晔',
            'category': '历史',
            'description': '本书是纪传体断代史，记载了东汉一朝195年的历史。与《史记》、《汉书》、《三国志》合称"前四史"。',
            'publisher': '中华书局',
            'publish_date': '公元445年',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-101-09554-1',
            'title': '三国志',
            'author': '陈寿',
            'category': '历史',
            'description': '本书是纪传体国别史，记载了魏蜀吴三国的历史。与《史记》、《汉书》、《后汉书》合称"前四史"。',
            'publisher': '中华书局',
            'publish_date': '公元280年',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        }
    ],
    '哲学': [
        {
            'isbn': '978-7-100-04620-4',
            'title': '论语',
            'author': '孔子',
            'category': '哲学',
            'description': '本书是儒家经典著作，记录了孔子及其弟子的言行。是中国古代最重要的思想文献之一，对中国文化产生了深远影响。',
            'publisher': '中华书局',
            'publish_date': '公元前479年',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04621-1',
            'title': '道德经',
            'author': '老子',
            'category': '哲学',
            'description': '本书是道家经典著作，阐述了道家的哲学思想。全书仅五千余言，却蕴含了深刻的哲理，对后世产生了巨大影响。',
            'publisher': '中华书局',
            'publish_date': '公元前6世纪',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04622-9',
            'title': '庄子',
            'author': '庄子',
            'category': '哲学',
            'description': '本书是道家经典著作，以寓言的形式阐述了道家的哲学思想。文笔优美，思想深刻，是中国古代哲学的重要文献。',
            'publisher': '中华书局',
            'publish_date': '公元前4世纪',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04623-7',
            'title': '孟子',
            'author': '孟子',
            'category': '哲学',
            'description': '本书是儒家经典著作，记录了孟子的言行和思想。与《论语》并称"孔孟"，是儒家思想的重要文献。',
            'publisher': '中华书局',
            'publish_date': '公元前4世纪',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04624-5',
            'title': '大学',
            'author': '曾子',
            'category': '哲学',
            'description': '本书是儒家经典著作，阐述了修身齐家治国平天下的道理。是《四书》之一，对中国古代教育产生了重要影响。',
            'publisher': '中华书局',
            'publish_date': '公元前4世纪',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04625-2',
            'title': '中庸',
            'author': '子思',
            'category': '哲学',
            'description': '本书是儒家经典著作，阐述了中庸之道的哲学思想。是《四书》之一，对中国古代哲学产生了重要影响。',
            'publisher': '中华书局',
            'publish_date': '公元前4世纪',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04626-0',
            'title': '周易',
            'author': '周文王',
            'category': '哲学',
            'description': '本书是中国古代占卜和哲学著作，阐述了阴阳五行的哲学思想。是《五经》之一，对中国文化产生了深远影响。',
            'publisher': '中华书局',
            'publish_date': '公元前11世纪',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-04627-8',
            'title': '孙子兵法',
            'author': '孙武',
            'category': '哲学',
            'description': '本书是中国古代军事著作，阐述了战争的战略和战术思想。被誉为"兵学圣典"，对后世军事思想产生了巨大影响。',
            'publisher': '中华书局',
            'publish_date': '公元前6世纪',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        }
    ],
    '科学': [
        {
            'isbn': '978-7-03-015451-2',
            'title': '时间简史',
            'author': '史蒂芬·霍金',
            'category': '科学',
            'description': '本书是霍金的科普著作，以通俗易懂的方式介绍了宇宙的起源、发展和未来。是科学普及的经典之作。',
            'publisher': '湖南科学技术出版社',
            'publish_date': '1988-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015452-9',
            'title': '物种起源',
            'author': '查尔斯·达尔文',
            'category': '科学',
            'description': '本书是达尔文的科学著作，阐述了生物进化的理论。是生物学领域的奠基之作，对科学界产生了巨大影响。',
            'publisher': '商务印书馆',
            'publish_date': '1859-11-24',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015453-6',
            'title': '相对论',
            'author': '阿尔伯特·爱因斯坦',
            'category': '科学',
            'description': '本书是爱因斯坦的科学著作，阐述了狭义相对论和广义相对论。是物理学领域的革命性著作，对现代物理学产生了巨大影响。',
            'publisher': '北京大学出版社',
            'publish_date': '1916-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015454-3',
            'title': '量子力学',
            'author': '理查德·费曼',
            'category': '科学',
            'description': '本书是费曼的物理学著作，以通俗易懂的方式介绍了量子力学的基本概念。是物理学普及的经典之作。',
            'publisher': '上海科学技术出版社',
            'publish_date': '1965-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015455-0',
            'title': '基因传',
            'author': '悉达多·穆克吉',
            'category': '科学',
            'description': '本书是生物学科普著作，以生动的方式介绍了基因的发现和研究。是生物学普及的经典之作。',
            'publisher': '上海科学技术出版社',
            'publish_date': '2000-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015456-7',
            'title': '宇宙的琴弦',
            'author': '布莱恩·格林',
            'category': '科学',
            'description': '本书是格林的物理学著作，介绍了弦理论的基本概念。是理论物理学的前沿之作。',
            'publisher': '湖南科学技术出版社',
            'publish_date': '1999-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015457-4',
            'title': '混沌与分形',
            'author': '詹姆斯·格雷克',
            'category': '科学',
            'description': '本书是数学和物理学科普著作，介绍了混沌理论和分形几何。是复杂性科学的重要文献。',
            'publisher': '高等教育出版社',
            'publish_date': '1987-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-03-015458-1',
            'title': '生命是什么',
            'author': '埃尔温·薛定谔',
            'category': '科学',
            'description': '本书是薛定谔的科学哲学著作，探讨了生命的本质和意义。是科学哲学的重要文献。',
            'publisher': '上海科学技术出版社',
            'publish_date': '1944-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        }
    ],
    '艺术': [
        {
            'isbn': '978-7-505-71234-5',
            'title': '艺术的故事',
            'author': '贡布里希',
            'category': '艺术',
            'description': '本书是艺术史的经典著作，系统介绍了从史前到现代的艺术发展历程。是艺术普及的重要文献。',
            'publisher': '广西美术出版社',
            'publish_date': '2008-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71235-2',
            'title': '西方美术史',
            'author': '贡布里希',
            'category': '艺术',
            'description': '本书是西方艺术史的经典著作，详细介绍了从古代到现代的西方艺术发展历程。是艺术研究的重要文献。',
            'publisher': '广西美术出版社',
            'publish_date': '2010-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71236-9',
            'title': '中国美术史',
            'author': '王伯敏',
            'category': '艺术',
            'description': '本书是中国美术史的经典著作，系统介绍了从史前到现代的中国艺术发展历程。是艺术研究的重要文献。',
            'publisher': '人民美术出版社',
            'publish_date': '2012-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71237-6',
            'title': '设计心理学',
            'author': '唐纳德·诺曼',
            'category': '艺术',
            'description': '本书是设计心理学领域的经典著作，探讨了设计与人类心理的关系。是设计理论的重要文献。',
            'publisher': '中信出版社',
            'publish_date': '2010-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71238-3',
            'title': '写给大家看的设计书',
            'author': '原研哉',
            'category': '艺术',
            'description': '本书是设计普及的经典著作，以通俗易懂的方式介绍了设计的基本原理。是设计入门的重要文献。',
            'publisher': '广西师范大学出版社',
            'publish_date': '2016-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71239-0',
            'title': '色彩互动学',
            'author': '约瑟夫·阿尔伯斯',
            'category': '艺术',
            'description': '本书是色彩理论领域的经典著作，阐述了色彩与人类视觉的互动关系。是色彩研究的重要文献。',
            'publisher': '人民美术出版社',
            'publish_date': '2013-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71240-7',
            'title': '字体故事',
            'author': '西蒙·加菲尔德',
            'category': '艺术',
            'description': '本书是字体设计的经典著作，介绍了字体的发展历史和设计原理。是字体研究的重要文献。',
            'publisher': '中信出版社',
            'publish_date': '2011-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-505-71241-4',
            'title': '设计中的设计',
            'author': '原研哉',
            'category': '艺术',
            'description': '本书是设计理论的重要著作，探讨了设计中的设计哲学。是设计研究的重要文献。',
            'publisher': '广西师范大学出版社',
            'publish_date': '2018-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        }
    ],
    '经济': [
        {
            'isbn': '978-7-100-01720-3',
            'title': '国富论',
            'author': '亚当·斯密',
            'category': '经济',
            'description': '本书是经济学的奠基之作，阐述了自由市场经济的基本原理。是经济学领域的经典著作。',
            'publisher': '商务印书馆',
            'publish_date': '1776-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01721-0',
            'title': '资本论',
            'author': '卡尔·马克思',
            'category': '经济',
            'description': '本书是马克思主义政治经济学的奠基之作，阐述了资本主义的基本原理。是经济学领域的经典著作。',
            'publisher': '人民出版社',
            'publish_date': '1867-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01722-8',
            'title': '经济学原理',
            'author': '阿尔弗雷德·马歇尔',
            'category': '经济',
            'description': '本书是经济学的经典教材，系统介绍了经济学的基本原理。是经济学入门的重要文献。',
            'publisher': '商务印书馆',
            'publish_date': '1890-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01723-5',
            'title': '微观经济学',
            'author': '曼昆',
            'category': '经济',
            'description': '本书是微观经济学的经典教材，详细介绍了微观经济学的基本理论。是经济学学习的重要文献。',
            'publisher': '中国人民大学出版社',
            'publish_date': '1998-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01724-2',
            'title': '宏观经济学',
            'author': '曼昆',
            'category': '经济',
            'description': '本书是宏观经济学的经典教材，详细介绍了宏观经济学的基本理论。是经济学学习的重要文献。',
            'publisher': '中国人民大学出版社',
            'publish_date': '1998-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01725-9',
            'title': '博弈论',
            'author': '约翰·纳什',
            'category': '经济',
            'description': '本书是博弈论的经典著作，阐述了博弈论的基本原理和应用。是经济学研究的重要文献。',
            'publisher': '中国人民大学出版社',
            'publish_date': '1950-01-01',
            'total_copies': 3,
            'available_copies': 3,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01726-6',
            'title': '行为经济学',
            'author': '丹尼尔·卡尼曼',
            'category': '经济',
            'description': '本书是行为经济学的奠基之作，探讨了人类决策的非理性因素。是经济学研究的重要文献。',
            'publisher': '中国人民大学出版社',
            'publish_date': '2011-01-01',
            'total_copies': 4,
            'available_copies': 4,
            'status': '可借阅'
        },
        {
            'isbn': '978-7-100-01727-3',
            'title': '发展经济学',
            'author': '阿马蒂亚·森',
            'category': '经济',
            'description': '本书是发展经济学的经典著作，探讨了经济发展与人类福祉的关系。是经济学研究的重要文献。',
            'publisher': '中国人民大学出版社',
            'publish_date': '1999-01-01',
            'total_copies': 5,
            'available_copies': 5,
            'status': '可借阅'
        }
    ]
}

def insert_books():
    """插入图书数据到数据库"""
    if not os.path.exists(DATABASE):
        print(f"错误：数据库文件 {DATABASE} 不存在")
        return
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    total_books = 0
    success_count = 0
    error_count = 0
    
    print("开始插入图书数据...")
    print("=" * 50)
    
    for category, books in real_books.items():
        print(f"\n处理分类: {category}")
        print("-" * 50)
        
        for i, book in enumerate(books, 1):
            try:
                cursor.execute('''
                    INSERT INTO books (isbn, title, author, category, description, publisher, publish_date, total_copies, available_copies, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    book['isbn'],
                    book['title'],
                    book['author'],
                    book['category'],
                    book['description'],
                    book['publisher'],
                    book['publish_date'],
                    book['total_copies'],
                    book['available_copies'],
                    book['status']
                ))
                success_count += 1
                print(f"  [{i:2d}] ✓ {book['title']}")
            except sqlite3.IntegrityError as e:
                error_count += 1
                print(f"  [{i:2d}] ✗ {book['title']} - 已存在")
            except Exception as e:
                error_count += 1
                print(f"  [{i:2d}] ✗ {book['title']} - 错误: {e}")
        
        total_books += len(books)
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print(f"插入完成！")
    print(f"总图书数: {total_books}")
    print(f"成功插入: {success_count}")
    print(f"已存在/错误: {error_count}")
    print("=" * 50)

if __name__ == '__main__':
    insert_books()

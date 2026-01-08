#!/usr/bin/env python3
"""
Test why AnimesDigital doesn't appear with AniList titles.
"""

from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository

repo = Repository()
repo.register(AnimesDigital)

# Test 1: Search com título simples (funciona)
print("TEST 1: Busca simples")
print("="*60)
repo.clear_search_results()
AnimesDigital.search_anime("jujutsu kaisen")
print("Query: 'jujutsu kaisen'")
print(f"Resultados: {len(repo.anime_to_urls)}")
for title in list(repo.anime_to_urls.keys())[:3]:
    print(f"  - {title}")

# Test 2: Search com título do AniList (pode não funcionar)
print("\n" + "="*60)
print("TEST 2: Busca com título AniList")
print("="*60)
repo.clear_search_results()
anilist_title = "Jujutsu Kaisen / JUJUTSU KAISEN"
print(f"Query: '{anilist_title}'")

try:
    AnimesDigital.search_anime(anilist_title)
    results = len(repo.anime_to_urls)
    print(f"Resultados: {results}")
    if results > 0:
        for title in list(repo.anime_to_urls.keys())[:3]:
            print(f"  - {title}")
    else:
        print("  ❌ Nenhum resultado!")
except Exception as e:
    print(f"❌ Erro: {e}")

# Test 3: Normalize para ver a diferença
print("\n" + "="*60)
print("TEST 3: Normalização de títulos")
print("="*60)

def normalize(text):
    text = text.lower()
    for char in ["-", ":", "(", ")", "!", "?", "."]:
        text = text.replace(char, " ")
    return " ".join(text.split())

title1 = "jujutsu kaisen"
title2 = "Jujutsu Kaisen / JUJUTSU KAISEN"

norm1 = normalize(title1)
norm2 = normalize(title2)

print(f"'{title1}' → '{norm1}'")
print(f"'{title2}' → '{norm2}'")
print(f"São iguais? {norm1 == norm2}")
print(f"'{norm1}' in '{norm2}'? {norm1 in norm2}")

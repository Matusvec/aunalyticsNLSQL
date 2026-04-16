# LLM Benchmark Report

| case | ollama | gemini |
|---|---|---|
| count_usa_customers | ✅ 1.4s | ✅ 1.5s |
| total_artists | ✅ 1.1s | ✅ 2.1s |
| total_tracks | ✅ 0.9s | ✅ 1.3s |
| top_3_spenders | ❌ 4.5s | ✅ 1.9s |
| bottom_3_spenders | ✅ 4.0s | ✅ 2.0s |
| longest_track | ✅ 1.1s | ✅ 1.7s |
| tracks_per_genre_top3 | ✅ 1.9s | ✅ 1.8s |
| countries_with_customers | ✅ 1.0s | ✅ 1.5s |
| most_prolific_artist | ✅ 3.2s | ✅ 1.7s |
| rock_track_count | ✅ 2.2s | ✅ 1.3s |
| top_country_revenue | ✅ 2.0s | ✅ 1.4s |
| invoices_in_2009 | ✅ 1.7s | ✅ 1.5s |
| playlists_count | ✅ 1.5s | ✅ 1.3s |
| employees_count | ✅ 1.1s | ✅ 1.3s |

## Summary

- **ollama** — 13/14 passed (93%), avg 2.0s/case
- **gemini** — 14/14 passed (100%), avg 1.6s/case

## Failures

### ollama

**top_3_spenders** — wrong result
- sql: `SELECT c.CustomerId AS CustomerId, COUNT(ii.TrackId) AS TrackCount, SUM(ii.UnitPrice * ii.Quantity) AS TotalSpent FROM customers AS c JOIN invoices AS i ON c.CustomerId = i.CustomerId JOIN invoice_items AS ii ON i.InvoiceId = ii.InvoiceId GROUP BY c.CustomerId, ii.TrackId ORDER BY TotalSpent DESC LIMIT 3`
- ❌ missing expected rows: [('Helena',), ('Richard',), ('Luis',)]


### gemini

(none)

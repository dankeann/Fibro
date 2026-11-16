-- number of papers where year is null
SELECT COUNT(*) 
FROM papers 
WHERE year IS NULL;

-- nuumber of papers for each publication type
SELECT pub_type, COUNT(*) AS n 
FROM publication_types
GROUP BY pub_type 
ORDER BY n DESC
# Test các câu hỏi thực tế với Knowledge Graph

$questions = @(
    "Sinh viên muốn chuyển ngành cần điều kiện gì?",
    "Tôi có thể chuyển trường không?",
    "ĐTBC bao nhiêu thì được chuyển ngành?",
    "Năm nhất có được chuyển ngành không?",
    "Điều kiện để thi kết thúc học phần là gì?",
    "Phải đi học bao nhiêu phần trăm mới được thi?"
)

$counter = 1
foreach ($question in $questions) {
    Write-Host "`n" -NoNewline
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "TEST $counter : $question" -ForegroundColor Yellow
    Write-Host "=" * 80 -ForegroundColor Cyan
    
    $body = @{
        query = $question
        session_id = "test_real_$counter"
    } | ConvertTo-Json -Depth 10
    
    # Fix encoding
    $body = [System.Text.Encoding]::UTF8.GetBytes($body)
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/chat" `
            -Method POST `
            -ContentType "application/json; charset=utf-8" `
            -Body $body
        
        Write-Host "`n📝 ANSWER:" -ForegroundColor Green
        Write-Host $response.response
        
        Write-Host "`n🔍 METADATA:" -ForegroundColor Magenta
        Write-Host "   - Used KG: $($response.rag_context.use_knowledge_graph)"
        Write-Host "   - Complexity: $($response.processing_stats.plan_complexity)"
        Write-Host "   - Documents: $($response.rag_context.total_documents)"
        
        if ($response.rag_context.use_knowledge_graph) {
            $content = $response.rag_context.documents[0].content
            if ($content -match "Content:") {
                Write-Host "   - ✅ KG Content included!" -ForegroundColor Green
            } else {
                Write-Host "   - ❌ KG Content missing!" -ForegroundColor Red
            }
        }
        
    } catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
    }
    
    $counter++
    Start-Sleep -Seconds 2
}

Write-Host "`n" -NoNewline
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "✅ ALL TESTS COMPLETED" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan

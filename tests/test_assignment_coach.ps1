# Comprehensive Test Script - Multiple Assignments with Formatted Output
# Tests various subjects and difficulty levels

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "ASSIGNMENT COACH - COMPREHENSIVE TEST" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Login
Write-Host "Logging in..." -ForegroundColor Yellow
$token = (Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method Post -Body (@{email="test@example.com"; password="password"} | ConvertTo-Json) -ContentType "application/json").token
Write-Host "[OK] Login successful`n" -ForegroundColor Green

# Function to display formatted results
function Show-AssignmentGuidance {
    param($result, $testNumber, $testName)
    
    $guidance = ($result.response | ConvertFrom-Json).response
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "TEST $testNumber : $testName" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    Write-Host "`nMETADATA:" -ForegroundColor Magenta
    Write-Host "   Execution: $([math]::Round($result.metadata.executionTime, 2)) ms | Cached: $($result.metadata.cached)" -ForegroundColor Gray
    
    Write-Host "`nSUMMARY:" -ForegroundColor Cyan
    $summary = $guidance.assignment_summary
    if ($summary.Length -gt 150) {
        Write-Host "   $($summary.Substring(0, 150))..." -ForegroundColor White
    } else {
        Write-Host "   $summary" -ForegroundColor White
    }
    
    Write-Host "`nTASKS ($($guidance.task_plan.Count)):" -ForegroundColor Yellow
    foreach ($task in $guidance.task_plan | Select-Object -First 3) {
        Write-Host "   [$($task.step)] $($task.task) - $($task.estimated_time)" -ForegroundColor White
    }
    if ($guidance.task_plan.Count -gt 3) {
        Write-Host "   ... and $($guidance.task_plan.Count - 3) more" -ForegroundColor Gray
    }
    
    Write-Host "`nRESOURCES ($($guidance.recommended_resources.Count)):" -ForegroundColor Green
    foreach ($res in $guidance.recommended_resources | Select-Object -First 2) {
        Write-Host "   [$($res.type.ToUpper())] $($res.title)" -ForegroundColor White
    }
    if ($guidance.recommended_resources.Count -gt 2) {
        Write-Host "   ... and $($guidance.recommended_resources.Count - 2) more" -ForegroundColor Gray
    }
    
    Write-Host "`nFEEDBACK:" -ForegroundColor Magenta
    Write-Host "   $($guidance.feedback)" -ForegroundColor White
    
    Write-Host ""
}

# Test 1: E-commerce Database Schema (Advanced)
Write-Host "[1/6] Testing E-commerce Database Schema..." -ForegroundColor Yellow
$body1 = @{
    agentId = "assignment-coach"
    request = @{
        agent_name = "assignment_coach_agent"
        intent = "generate_assignment_guidance"
        payload = @{
            student_id = "stu_103"
            assignment_title = "E-commerce Database Schema"
            assignment_description = "Design a normalized database schema for an e-commerce platform"
            subject = "Database Systems"
            deadline = "2025-12-20"
            difficulty = "Advanced"
            student_profile = @{
                learning_style = "reading"
                progress = 0.2
                skills = @("SQL")
                weaknesses = @("normalization")
            }
        }
    } | ConvertTo-Json -Depth 10
    priority = 1
    autoRoute = $false
} | ConvertTo-Json -Depth 10

$result1 = Invoke-RestMethod -Uri "http://localhost:8000/api/supervisor/request" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body1 -ContentType "application/json"
Show-AssignmentGuidance -result $result1 -testNumber "1/6" -testName "E-commerce Database (Advanced)"

Start-Sleep -Seconds 1

# Test 2: Python Calculator (Beginner)
Write-Host "[2/6] Testing Python Calculator..." -ForegroundColor Yellow
$body2 = @{
    agentId = "assignment-coach"
    request = @{
        agent_name = "assignment_coach_agent"
        intent = "generate_assignment_guidance"
        payload = @{
            student_id = "stu_101"
            assignment_title = "Build a Simple Calculator in Python"
            assignment_description = "Create a command-line calculator with basic arithmetic operations"
            subject = "Python Programming"
            deadline = "2025-11-25"
            difficulty = "Beginner"
            student_profile = @{
                learning_style = "hands-on"
                progress = 0.0
                skills = @("problem-solving")
                weaknesses = @("coding")
            }
        }
    } | ConvertTo-Json -Depth 10
    priority = 1
    autoRoute = $false
} | ConvertTo-Json -Depth 10

$result2 = Invoke-RestMethod -Uri "http://localhost:8000/api/supervisor/request" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body2 -ContentType "application/json"
Show-AssignmentGuidance -result $result2 -testNumber "2/6" -testName "Python Calculator (Beginner)"

Start-Sleep -Seconds 1

# Test 3: Machine Learning Project (Intermediate)
Write-Host "[3/6] Testing Machine Learning Project..." -ForegroundColor Yellow
$body3 = @{
    agentId = "assignment-coach"
    request = @{
        agent_name = "assignment_coach_agent"
        intent = "generate_assignment_guidance"
        payload = @{
            student_id = "stu_201"
            assignment_title = "Customer Churn Prediction Model"
            assignment_description = "Build a machine learning model to predict customer churn using Python and scikit-learn"
            subject = "Machine Learning"
            deadline = "2025-12-15"
            difficulty = "Intermediate"
            student_profile = @{
                learning_style = "hands-on"
                progress = 0.3
                skills = @("Python", "statistics")
                weaknesses = @("feature engineering", "model evaluation")
            }
        }
    } | ConvertTo-Json -Depth 10
    priority = 1
    autoRoute = $false
} | ConvertTo-Json -Depth 10

$result3 = Invoke-RestMethod -Uri "http://localhost:8000/api/supervisor/request" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body3 -ContentType "application/json"
Show-AssignmentGuidance -result $result3 -testNumber "3/6" -testName "ML Churn Prediction (Intermediate)"

Start-Sleep -Seconds 1

# Test 4: Web Development Portfolio (Intermediate)
Write-Host "[4/6] Testing Web Portfolio..." -ForegroundColor Yellow
$body4 = @{
    agentId = "assignment-coach"
    request = @{
        agent_name = "assignment_coach_agent"
        intent = "generate_assignment_guidance"
        payload = @{
            student_id = "stu_102"
            assignment_title = "Responsive Portfolio Website"
            assignment_description = "Design and develop a responsive portfolio website using HTML, CSS, and JavaScript with modern design principles"
            subject = "Web Development"
            deadline = "2025-12-10"
            difficulty = "Intermediate"
            student_profile = @{
                learning_style = "visual"
                progress = 0.4
                skills = @("HTML", "CSS")
                weaknesses = @("JavaScript", "responsive design")
            }
        }
    } | ConvertTo-Json -Depth 10
    priority = 1
    autoRoute = $false
} | ConvertTo-Json -Depth 10

$result4 = Invoke-RestMethod -Uri "http://localhost:8000/api/supervisor/request" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body4 -ContentType "application/json"
Show-AssignmentGuidance -result $result4 -testNumber "4/6" -testName "Web Portfolio (Intermediate)"

Start-Sleep -Seconds 1

# Test 5: Cybersecurity Audit (Advanced)
Write-Host "[5/6] Testing Cybersecurity Audit..." -ForegroundColor Yellow
$body5 = @{
    agentId = "assignment-coach"
    request = @{
        agent_name = "assignment_coach_agent"
        intent = "generate_assignment_guidance"
        payload = @{
            student_id = "stu_106"
            assignment_title = "Network Security Audit Report"
            assignment_description = "Conduct comprehensive security audit and penetration testing of a test network infrastructure"
            subject = "Cybersecurity"
            deadline = "2025-12-18"
            difficulty = "Advanced"
            student_profile = @{
                learning_style = "hands-on"
                progress = 0.25
                skills = @("networking", "Linux")
                weaknesses = @("documentation", "reporting")
            }
        }
    } | ConvertTo-Json -Depth 10
    priority = 1
    autoRoute = $false
} | ConvertTo-Json -Depth 10

$result5 = Invoke-RestMethod -Uri "http://localhost:8000/api/supervisor/request" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body5 -ContentType "application/json"
Show-AssignmentGuidance -result $result5 -testNumber "5/6" -testName "Security Audit (Advanced)"

Start-Sleep -Seconds 1

# Test 6: Mobile App Design (Beginner)
Write-Host "[6/6] Testing Mobile App Design..." -ForegroundColor Yellow
$body6 = @{
    agentId = "assignment-coach"
    request = @{
        agent_name = "assignment_coach_agent"
        intent = "generate_assignment_guidance"
        payload = @{
            student_id = "stu_105"
            assignment_title = "Fitness Tracker App Design"
            assignment_description = "Create wireframes and mockups for a mobile fitness tracking application with modern UI/UX principles"
            subject = "Mobile App Design"
            deadline = "2025-11-30"
            difficulty = "Beginner"
            student_profile = @{
                learning_style = "visual"
                progress = 0.1
                skills = @("creativity", "sketching")
                weaknesses = @("design tools", "prototyping")
            }
        }
    } | ConvertTo-Json -Depth 10
    priority = 1
    autoRoute = $false
} | ConvertTo-Json -Depth 10

$result6 = Invoke-RestMethod -Uri "http://localhost:8000/api/supervisor/request" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body6 -ContentType "application/json"
Show-AssignmentGuidance -result $result6 -testNumber "6/6" -testName "Mobile App Design (Beginner)"

# Final Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] ALL 6 TESTS COMPLETED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nDifficulty Levels Tested:" -ForegroundColor Yellow
Write-Host "  - Beginner: 2 tests" -ForegroundColor White
Write-Host "  - Intermediate: 2 tests" -ForegroundColor White
Write-Host "  - Advanced: 2 tests" -ForegroundColor White
Write-Host "`nSubjects Covered:" -ForegroundColor Yellow
Write-Host "  - Database Systems" -ForegroundColor White
Write-Host "  - Python Programming" -ForegroundColor White
Write-Host "  - Machine Learning" -ForegroundColor White
Write-Host "  - Web Development" -ForegroundColor White
Write-Host "  - Cybersecurity" -ForegroundColor White
Write-Host "  - Mobile App Design" -ForegroundColor White
Write-Host "`n========================================`n" -ForegroundColor Cyan

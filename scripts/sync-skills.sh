#!/bin/bash

# Script para sincronizar skills entre repo e ~/.cursor/skills/
# Uso: ./scripts/sync-skills.sh [--dry-run]

set -e

REPO_SKILLS_DIR="skills"
CURSOR_SKILLS_DIR="$HOME/.cursor/skills"

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 Modo dry-run (apenas mostrará mudanças)"
fi

# Skills pipeline a sincronizar
PIPELINE_SKILLS=(
    "pipeline-story-analyzer"
    "pipeline-story-planner"
    "pipeline-task-breaker"
    "pipeline-task-planner"
    "pipeline-plan-validator"
    "pipeline-task-definer"
    "pipeline-review-backend"
    "pipeline-review-frontend"
    "pipeline-pr-responder"
    "pipeline-pr-updater"
    "pipeline-create-technical-docs"
    "pipeline-review-documentation"
)

# Skills originais (NÃO sincronizar automaticamente)
ORIGINAL_SKILLS=(
    "skill-story-planner"
    "skill-jira-task-creator"
    "skill-task-planner"
    "skill-plan-improvement"
    "skill-back-review-changes"
    "skill-front-review-changes"
    "skill-address-pr-reviews"
)

echo "====================================="
echo "Sincronização de Skills"
echo "====================================="
echo ""

# 1. Sincronizar pipeline skills (repo → local)
echo "📋 Sincronizando skills pipeline (repo → ~/.cursor/skills/)..."
echo ""

for skill in "${PIPELINE_SKILLS[@]}"; do
    source_file="$REPO_SKILLS_DIR/$skill/SKILL.md"
    target_dir="$CURSOR_SKILLS_DIR/$skill"
    target_file="$target_dir/SKILL.md"
    
    if [[ ! -f "$source_file" ]]; then
        echo "⚠️  $skill: arquivo fonte não encontrado"
        continue
    fi
    
    # Criar diretório se não existe
    if [[ ! -d "$target_dir" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            echo "➕  $skill: criaria diretório $target_dir"
        else
            mkdir -p "$target_dir"
            echo "➕  $skill: diretório criado"
        fi
    fi
    
    # Comparar arquivos (se target existe)
    if [[ -f "$target_file" ]]; then
        if diff -q "$source_file" "$target_file" > /dev/null 2>&1; then
            echo "✅  $skill: já sincronizado"
        else
            if [[ "$DRY_RUN" == true ]]; then
                echo "🔄  $skill: precisaria atualizar (DIFERENTE)"
            else
                cp "$source_file" "$target_file"
                echo "🔄  $skill: atualizado"
            fi
        fi
    else
        if [[ "$DRY_RUN" == true ]]; then
            echo "➕  $skill: copiaria para $target_file"
        else
            cp "$source_file" "$target_file"
            echo "➕  $skill: copiado"
        fi
    fi
done

echo ""
echo "====================================="
echo "Resumo"
echo "====================================="
echo ""
echo "✅ Skills pipeline sincronizadas"
echo ""
echo "⚠️  Skills originais (skill-*) NÃO foram tocadas"
echo "   (edite-as manualmente se necessário)"
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo "💡 Execute sem --dry-run para aplicar mudanças"
fi

#!/bin/bash
# Navigator ASCII Logo - Blue N, Red A, Blue V (compass arrow)

VERSION="${1:-5.3.0}"

BLUE='\033[1;34m'
RED='\033[1;31m'
WHITE='\033[1;37m'
GRAY='\033[90m'
NC='\033[0m'

echo ""
printf "${BLUE}███╗   ██╗${NC} ${RED} █████╗ ${NC}${BLUE}██╗   ██╗${NC}\n"
printf "${BLUE}████╗  ██║${NC} ${RED}██╔══██╗${NC}${BLUE}██║   ██║${NC}\n"
printf "${BLUE}██╔██╗ ██║${NC} ${RED}███████║${NC}${BLUE}██║   ██║${NC}  ${WHITE}v${VERSION}${NC}\n"
printf "${BLUE}██║╚██╗██║${NC} ${RED}██╔══██║${NC}${BLUE}╚██╗ ██╔╝${NC}  ${GRAY}Finish What You Start${NC}\n"
printf "${BLUE}██║ ╚████║${NC} ${RED}██║  ██║${NC}${BLUE} ╚████╔╝ ${NC}\n"
printf "${BLUE}╚═╝  ╚═══╝${NC} ${RED}╚═╝  ╚═╝${NC}${BLUE}  ╚═══╝  ${NC}\n"
echo ""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse
import re

class PavimentosFixTestCase(TestCase):
    """
    Test case to verify the pavimentos.js fix that prevents 
    empreendimento fields from triggering pavimentos calculations.
    """
    
    def setUp(self):
        """Set up test client"""
        self.client = Client()
        
    def test_pavimentos_js_regex_pattern(self):
        """
        Test that the JavaScript regex pattern in pavimentos.js
        correctly filters field names to only match pavimento fields.
        """
        # Read the pavimentos.js file content
        with open('/home/runner/work/prognoz/prognoz/viabilidade/static/viabilidade/pavimentos.js', 'r') as f:
            js_content = f.read()
            
        # Verify the regex pattern exists in the file
        regex_pattern = r"String\(e\.target\.name\)\.match\(/\^\(rep\|area\|coef\|tipo\)_\(\\d\+\)\$/"
        self.assertTrue(
            re.search(regex_pattern, js_content),
            "The correct regex pattern should be present in pavimentos.js"
        )
        
        # Test the actual regex behavior  
        test_regex = re.compile(r'^(rep|area|coef|tipo)_(\d+)$')
        
        # Fields that should NOT match (empreendimento fields)
        empreendimento_fields = [
            'area_privativa',
            'custo_area_privativa',
            'area_total_construcao',
            'area_comum'
        ]
        
        for field in empreendimento_fields:
            match = test_regex.match(field)
            self.assertIsNone(
                match, 
                f"Field '{field}' should NOT match the pavimentos regex"
            )
            
        # Fields that should match (pavimento fields)  
        pavimento_fields = [
            ('area_1', '1'),
            ('rep_12', '12'), 
            ('coef_5', '5'),
            ('tipo_3', '3')
        ]
        
        for field, expected_id in pavimento_fields:
            match = test_regex.match(field)
            self.assertIsNotNone(
                match,
                f"Field '{field}' should match the pavimentos regex"
            )
            self.assertEqual(
                match.group(2), expected_id,
                f"Field '{field}' should extract pavimento ID '{expected_id}'"
            )
    
    def test_pavimentos_js_file_exists(self):
        """Test that the pavimentos.js file exists and is accessible"""
        import os
        js_path = '/home/runner/work/prognoz/prognoz/viabilidade/static/viabilidade/pavimentos.js'
        self.assertTrue(
            os.path.exists(js_path),
            "pavimentos.js file should exist"
        )
        
        # Verify file contains expected functions
        with open(js_path, 'r') as f:
            content = f.read()
            
        expected_functions = [
            'parseNumBR',
            'formatBR', 
            'updateAreaEq',
            'updateAreaConstr',
            'atualizaCoef',
            'recalcTotais'
        ]
        
        for func_name in expected_functions:
            self.assertIn(
                f'function {func_name}',
                content,
                f"Function '{func_name}' should be defined in pavimentos.js"
            )
    
    def test_problem_statement_requirements(self):
        """
        Verify that the fix matches exactly what was described 
        in the problem statement.
        """
        with open('/home/runner/work/prognoz/prognoz/viabilidade/static/viabilidade/pavimentos.js', 'r') as f:
            js_content = f.read()
        
        # Check for the specific regex pattern mentioned in the problem statement
        self.assertIn(
            '/^(rep|area|coef|tipo)_(\\d+)$/',
            js_content,
            "Should contain the exact regex pattern from problem statement"
        )
        
        # Check for the comment explaining the change
        self.assertIn(
            'Only handle input events for pavimento fields',
            js_content,
            "Should contain comment explaining the restriction"
        )
        
        # Verify the event listener structure
        self.assertIn(
            "document.addEventListener('input', function(e)",
            js_content,
            "Should have input event listener"
        )
        
        # Verify the pattern matching logic
        self.assertIn(
            'const m = String(e.target.name).match',
            js_content,
            "Should use String().match() for pattern matching"
        )
        
        self.assertIn(
            'if (!m) return;',
            js_content,
            "Should return early if pattern doesn't match"
        )
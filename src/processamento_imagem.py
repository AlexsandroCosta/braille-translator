import cv2
import numpy
import math

class ProcessadorImagem:
    def __init__(self, caminho_imagem: str):
        # Carregar imagem
        self.imagem_original = self._carregar_imagem(caminho_imagem)
        self.altura, self.largura = self.imagem_original.shape[:2]
        self.imagem_processada = self.processar_imagem()

    def _carregar_imagem(self, caminho: str) -> numpy.ndarray:
        """Carrega a imagem e verifica se foi bem sucedido."""
        imagem = cv2.imread(caminho)
        if imagem is None:
            raise IOError(f'Não foi possível abrir a imagem: {caminho}')
        
        return imagem

    def processar_imagem(self) -> numpy.ndarray:

        imagem = self._pre_processamento()
        imagem = self._binarizar_imagem(imagem)
        imagem = self._aplicar_morfologia(imagem)

        return self._remover_ruido(imagem)

    def _pre_processamento(self) -> numpy.ndarray:
        # Conversão para escala de cinza
        imagem = cv2.cvtColor(self.imagem_original, cv2.COLOR_BGR2GRAY)
        
        # Correção de gamma (ajuste de brilho/contraste)
        imagem = self._correcao_gamma(imagem)

        return self._aplicar_clahe(imagem)
    
    def _correcao_gamma(self, imagem: numpy.ndarray) -> numpy.ndarray:
        gamma = self._calcular_gamma(imagem)

        tabela = numpy.array([((i/255.0)**(1.0/gamma)) * 255 for i in numpy.arange(0, 256)]).astype('uint8')
        
        return cv2.LUT(imagem, tabela)
    
    def _calcular_gamma(self, imagem:numpy.ndarray) -> float:
        brilho = numpy.mean(imagem)
        if brilho < 5: return 3.0
        if brilho > 250: return 0.4

        gamma = math.log(0.5) / math.log(brilho/255)

        return numpy.clip(gamma, 0.4, 3.0)
    
    def _aplicar_clahe(self, imagem: numpy.ndarray) -> numpy.ndarray:
        # Aplicação do CLAHE (Equalização Adaptativa de Histograma) para melhorar o contraste local da imagem.
        # O 'clipLimit' controla o limite de contraste e o 'tileGridSize' define o tamanho dos blocos para a equalização.
        clahe = cv2.createCLAHE(
            clipLimit = 2.0,
            tileGridSize = (8, 8) if max(self.altura, self.largura) < 2000 else (16, 16)
        )
        imagem = clahe.apply(imagem)

        return self._reduzir_ruido(imagem)
    
    def _reduzir_ruido(self, imagem: numpy.ndarray) -> numpy.ndarray:
        imagem_suavizada = cv2.medianBlur(imagem, 3)
        
        return cv2.GaussianBlur(imagem_suavizada, (5, 5), 0)

    def _binarizar_imagem(self, imagem: numpy.ndarray) -> numpy.ndarray:
        # Limiarização adaptativa com parâmetros dinâmicos(para destacar pontos)
        block_size = max(3, int(min(self.altura, self.largura) * 0.02) // 2 * 2 + 1)
        
        return cv2.adaptiveThreshold(
            imagem, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            block_size, 3
        )
    
    def _aplicar_morfologia(self, imagem: numpy.ndarray) -> numpy.ndarray:
        tamanho_kernel = max(1, int(min(self.altura, self.largura)*0.005))
        tamanho_kernel = tamanho_kernel + 1 if tamanho_kernel % 2 == 0 else tamanho_kernel

        # Operações morfológicas: erosão para separar pontos conectados e dilatação para recuperar forma
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (tamanho_kernel, tamanho_kernel))
        # imagem_erodida = cv2.erode(imagem_binaria, kernel, iterations=1)
        # imagem_processada = cv2.dilate(imagem_erodida, kernel, iterations=1)

        abertura = cv2.morphologyEx(imagem, cv2.MORPH_OPEN, kernel)
        fechamento = cv2.morphologyEx(abertura, cv2.MORPH_CLOSE, kernel, iterations=1)

        return fechamento

    def _remover_ruido(self, imagem:numpy.ndarray) -> numpy.ndarray:
        # Encontrar comOI: 10.1109/SCISISIS61014.2024.10759883ponentes conectados
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(imagem), 
            connectivity=8
        )

        mascara = numpy.zeros_like(imagem, dtype=numpy.uint8)

        if n_labels < 2:
            return imagem

        areas = stats[1:, cv2.CC_STAT_AREA]
        if not areas.size:
            return imagem

        # Cálculo dinâmico de limiares baseado na distribuição de áreas
        q25, q75 = numpy.percentile(areas, [25, 75])
        iqr = q75 - q25
        limiar_min = max(3, q25 - 1.5 * iqr)
        limiar_max = q75 + 1.5 * iqr

        for i in range(1, n_labels):  # Ignorar o fundo (componente 0)
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]

             # Filtros combinados
            if (limiar_min < area < limiar_max and
                0.7 < width/height < 1.3 and
                (width + height) * 0.25 > numpy.sqrt(area/numpy.pi) and
                area > numpy.pi * (min(width, height)/2)**2 * 0.6):
                
                mascara[labels == i] = 255
        
        # Reaplicar máscara mantendo a orientação original
        resultado = cv2.bitwise_and(imagem, imagem, mask=cv2.bitwise_not(mascara))
        return resultado
    
    def mostrar_resultados(self):
        cv2.imshow('Original', self.imagem_original)
        cv2.imshow('Processada', self.imagem_processada)
        cv2.waitKey(0)
        cv2.destroyAllWindows()